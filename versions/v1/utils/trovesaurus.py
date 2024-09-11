from pydantic import BaseModel, Field, field_validator, validator

from datetime import datetime
from enum import Enum
from typing import Union, Optional
from beanie import Document, Indexed


class TrovesaurusModFile(BaseModel):
    id: int = Field(alias="fileid")
    version: str
    date: int
    downloads: int
    changes: str
    format: str
    hash: str = Field(default="")


class ModAuthor(BaseModel):
    ID: Optional[int]
    Username: Optional[str]
    Avatar: Optional[str]
    Role: Optional[str]


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
    notes: str
    authors: list[ModAuthor]
    likes: int
    image_full_url: str = Field(alias="image_full")
    files: list[TrovesaurusModFile] = Field(alias="downloads")
    obsolete: int

    @field_validator("image_url", "image_full_url")
    @classmethod
    def check_url(cls, v):
        if not v.startswith("https"):
            return ""
        return v


class SearchCache(Document):
    id: Indexed(int)
    name: Indexed(str)
    type: Indexed(str)
    sub_type: Indexed(str)
    views: int
    downloads: int
    likes: int
    authors: list[ModAuthor]


class ModFileType(Enum):
    TMOD = "tmod"
    ZIP = "zip"
    CONFIG = "config"


class ModFile(BaseModel):
    file_id: int = Field(alias="fileid")
    type: ModFileType = Field(alias="format")
    is_config: bool = Field(alias="extra", default=False)
    version: str
    changes: str
    created_at: Union[int, datetime] = Field(alias="date")
    downloads: int
    hash: str = Field(default="")

    @validator("created_at")
    def parse_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.utcfromtimestamp(value)

    @validator("version")
    def parse_version(cls, value, values):
        if values["is_config"]:
            return "config"
        if not value.strip():
            return f"File: [{str(values['file_id'])}]"
        return value


class Mod(BaseModel):
    id: int
    name: str
    type: str
    subtype: str
    description: str
    created_at: datetime = Field(alias="date")
    views: int
    replacements: str = Field(alias="replaces")
    downloads: int = Field(alias="totaldownloads")
    thumbnail_url: str = Field(alias="image")
    user_id: int = Field(alias="userid")
    notes: str
    likes: int = Field(alias="votes")
    author: str
    image_url: str = Field(alias="image_full")
    file_objs: list[ModFile] = Field(alias="downloads", default_factory=list)
    installed: bool = False
    installed_file: ModFile = None

    def __contains__(self, item):
        return item in self.hashes

    @property
    def hashes(self):
        return [file.hash for file in self.file_objs]

    @validator("created_at")
    def parse_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.utcfromtimestamp(value)

    @property
    def clean_description(self):
        desc = paragraph.sub(r"\1", self.description)
        desc = strong.sub(r"\1", desc)
        desc = img.sub(r"", desc)
        desc = anchor.sub(r"\1", desc)
        desc = ul.sub(r"", desc)
        desc = br.sub(r"", desc)
        desc = li.sub("\t\u2022 \\1", desc)
        return (
            desc.replace("&nbsp;", "").replace("&gt;", ">").replace("&lt;", "<").strip()
            or None
        )

    @property
    def url(self):
        return f"https://trovesaurus.com/mod={self.id}"
