from status import read_sysfs, write_sysfs, PROFILE

def get_profile_choices() -> list[str]:
    """Return the profiels this laptop supports, or an empty list if none"""
    choices = read_sysfs(PROFILE / "platform_profile_choices")
    if choices is None:
        return []
    return choices.split()

def set_profile(profile: str) -> bool:
    """Switch the performance profile, but only if the name is valid."""
    choices = get_profile_choices()
    if not choices:
        print("Performance profiles are not supported on this laptop")
        return False
    if profile not in choices:
        print(f"'{profile}' is not valid. Choose from: {', '.join(choices)}")
        return False
    return write_sysfs(PROFILE / "platform_profile", profile)

if __name__ == "__main__":
    print("Trying 'turbo':", set_profile("turbo"))
    print("Trying 'quiet':", set_profile("quiet"))
    print("Profile is now:", read_sysfs(PROFILE / "platform_profile"))