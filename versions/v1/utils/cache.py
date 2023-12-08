from enum import Enum

from .trovesaurus import TrovesaurusMod


class SortOrder(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class ModCache:
    """This class is used to cache data in memory."""

    def __init__(self):
        self._data = {}
        self._cached_queries = {}
        self._processed_hashes = {}

    def __str__(self):
        return f"<ModCache mods={len(self)}>"

    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter(self._data.values())

    def __len__(self):
        return len(self._data.keys())

    def __contains__(self, key):
        return key in self

    def __getitem__(self, key):
        return self._get_item(key)

    def __setitem__(self, key, value):
        self._add_item(key, value)

    def __delitem__(self, key):
        self._remove_item(key)

    def _add_item(self, key, value: TrovesaurusMod):
        """Add an item to the cache."""
        self._data[key] = value

    def _get_item(self, key):
        """Get an item from the cache."""
        return self._data.get(key)

    def _remove_item(self, key):
        """Remove an item from the cache."""
        del self._data[key]

    def is_populated(self):
        return bool(self._data)

    def clear(self):
        """Clear the cache."""
        self._data = {}

    def process_hashes(self):
        for mod in self:
            for file in mod.files:
                if file.hash:
                    self._processed_hashes[file.hash] = mod

    def get_sorted_fields(
            self,
            *fields: tuple[str, SortOrder],
            limit: int = None,
            offset: int = None
    ) -> list[dict]:
        url_query = ""
        url_query += "#".join(f"{field[0]}${field[1].value}" for field in fields)
        url_query += f"&limit={limit}" if limit else ""
        url_query += f"&offset={offset}" if offset else ""
        if url_query not in self._cached_queries:
            print("Not cached")
            self._cached_queries[url_query] = [
                mod.dict(by_alias=True)
                for mod in sorted(
                    self,
                    key=lambda m: tuple(
                        (
                            getattr(m, field[0])
                            if field[1] == SortOrder.ASCENDING
                            else -getattr(m, field[0])
                        ) for field in fields
                    )
                )[offset:][:limit]
            ]
        return self._cached_queries[url_query]


    def get_mod_tags(self) -> list[str]:
        tags = set()
        for mod in self:
            if mod.type:
                tags.add(mod.type)
        return sorted(list(tags))
    
    def get_mod_subtags(self) -> list[str]:
        tags = set()
        for mod in self:
            if mod.sub_type:
                tags.add(mod.sub_type)
        return sorted(list(tags))
    
    def get_mod_by_hash(self, hash):
        mod = self._processed_hashes.get(hash)
        if mod:
            return mod.dict(by_alias=True)
        
    def get_all_hashed_mods(self, hashes):
        mods = {}
        for hash in list(set(hashes)):
            mods[hash] = self.get_mod_by_hash(hash)
        return mods