from .database import Database

DEFAULTS = {"language": "en", "active_user_id": ""}
SUPPORTED_LANGUAGES = ("en", "ar")


class Settings:
    def __init__(self, db: Database):
        self.db = db

    @property
    def language(self) -> str:
        v = self.db.get_setting("language", DEFAULTS["language"])
        return v if v in SUPPORTED_LANGUAGES else "en"

    @language.setter
    def language(self, value: str):
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {value}")
        self.db.set_setting("language", value)

    @property
    def active_user_id(self):
        v = self.db.get_setting("active_user_id", "")
        if v and self.db.get_user(int(v)):
            return int(v)
        uid = self.db.ensure_default_user()
        self.db.set_setting("active_user_id", uid)
        return uid

    @active_user_id.setter
    def active_user_id(self, uid: int):
        if not self.db.get_user(uid):
            raise ValueError("unknown user")
        self.db.set_setting("active_user_id", uid)

    @property
    def active_mouse_profile_id(self):
        """Active mouse profile of the active user, or None."""
        uid = self.active_user_id
        v = self.db.get_setting(f"active_mouse_profile:{uid}", "")
        if v:
            prof = self.db.get_mouse_profile(int(v))
            if prof and prof["user_id"] == uid:
                return prof["id"]
        return None

    @active_mouse_profile_id.setter
    def active_mouse_profile_id(self, profile_id):
        uid = self.active_user_id
        prof = self.db.get_mouse_profile(profile_id)
        if not prof or prof["user_id"] != uid:
            raise ValueError("unknown mouse profile")
        self.db.set_setting(f"active_mouse_profile:{uid}", profile_id)
