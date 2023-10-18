from pydantic import BaseModel, Field, field_validator


class TrovesaurusModFile(BaseModel):
    id: int = Field(alias="fileid")
    version: str
    date: int
    downloads: int
    changes: str
    format: str
    hash: str = Field(default="")


class TrovesaurusMod(BaseModel):
    id: int
    name: str
    type: str
    sub_type: str = Field(alias="subtype")
    description: str
    date: int
    views: int
    replacements: str = Field(alias="replaces")
    downloads: int = Field(alias="totaldownloads")
    image_url: str = Field(alias="image")
    user_id: int = Field(alias="userid")
    notes: str
    author: str
    likes: int = Field(alias="votes")
    image_full_url: str = Field(alias="image_full")
    files: list[TrovesaurusModFile] = Field(alias="downloads")

    @field_validator("image_url", "image_full_url")
    @classmethod
    def check_url(cls, v):
        if not v.startswith("https"):
            return ""
        return v
