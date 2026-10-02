from email.headerregistry import Address


def _mailbox(value: str) -> Address:
    if "\r" in value or "\n" in value:
        raise ValueError("A single email address is required")
    try:
        address = Address(addr_spec=value)
    except ValueError:
        raise ValueError("A single email address is required") from None
    if not address.username or not address.domain:
        raise ValueError("A single email address is required")
    return address
