from beanie import Document, Indexed
from ...utils.trovesaurus import TrovesaurusMod


class TrovesaurusEntry(Document):
    hash: Indexed(str, unique=True)
    mod: TrovesaurusMod
