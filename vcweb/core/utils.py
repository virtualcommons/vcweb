from distutils.util import strtobool


def confirm(prompt="Continue? (y/n) ", cancel_message="Aborted."):
    response = input(prompt)
    try:
        response_as_bool = strtobool(response)
    except ValueError:
        print("Invalid response ", response_as_bool, ". Please confirm with yes (y) or no (n).")
        confirm(prompt, cancel_message)
    if not response_as_bool:
        raise RuntimeError(cancel_message)
    return True
