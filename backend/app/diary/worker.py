import asyncio
import logging

from app.ai.client import AIConfigurationError, AIRequestError, CodysseyClient
from app.diary.composition import compose_diary
from app.diary.repository import DiaryRepository
from app.storage.diary_images import DiaryImageStorage, InvalidDiaryImage
from app.storage.supabase import StorageUploadError

logger = logging.getLogger(__name__)


class DiaryWorker:
    def __init__(self, repository: DiaryRepository, client: CodysseyClient, storage: DiaryImageStorage):
        self.repository, self.client, self.storage = repository, client, storage

    async def process(self, job: dict):
        code = "INTERNAL_ERROR"
        try:
            async with asyncio.timeout(540):
                summary = await self.repository.image_summary(job)
                options = job["options"]
                if options["prompt_version"] != "diary-v1":
                    raise AIConfigurationError("Unsupported prompt version")
                # Honor the models/options recorded at submission, even after environment changes.
                config = self.client.settings.model_copy(update={
                    "ai_text_model": options["text_model"], "ai_image_model": options["image_model"]})
                client = CodysseyClient(self.client.http_client, config)
                composition = await compose_diary(client, summary)
                data = await client.generate_image(composition.image_prompt, size=options["image_size"])
                stored = await self.storage.upload(data)
                await self.repository.finalize_image(job["id"], job["lease_token"],
                    composition.title, composition.encouragement_text, stored.bucket, stored.path)
                return
        except asyncio.CancelledError:
            # Leave the durable running record for expiry; do not regenerate on restart.
            raise
        except AIRequestError as error:
            code = error.code
        except (TimeoutError,):
            code = "TIMEOUT"
        except AIConfigurationError:
            code = "AI_NOT_CONFIGURED"
        except InvalidDiaryImage:
            code = "INVALID_IMAGE"
        except StorageUploadError:
            code = "STORAGE_FAILED"
        except Exception:
            pass
        try:
            await self.repository.fail_image(job["id"], job["lease_token"], code)
        except Exception:
            # If completion/failure acknowledgement was lost, DB state/lease decides the outcome.
            logger.warning("Diary worker could not record outcome")

    async def run(self):
        while True:
            try:
                # Missing/invalid keys must not consume queued records.
                self.client.build_image_request("configuration check", size=self.client.settings.ai_image_size)
                await self.repository.expire_image_leases()
                job = await self.repository.claim_image()
                if job:
                    await self.process(job)
                    continue
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Diary worker is unavailable")
            await asyncio.sleep(2)
