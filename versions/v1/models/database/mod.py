from __future__ import annotations

import base64
import io
import zipfile
import zlib
from hashlib import md5
from io import BytesIO
from pathlib import Path
from typing import Optional

from aiohttp import ClientSession
from binary_reader import BinaryReader
from pydantic import BaseModel
from toml import dumps

from ...utils.functions import (
    ReadLeb128,
    WriteLeb128,
    calculate_hash,
    chunks,
    get_attr,
)
from ...utils.trovesaurus import Mod, ModAuthor
from beanie import Document, Indexed


class NoFilesError(Exception): ...


class PropertyMalformedError(Exception): ...


class MissingPropertyError(Exception): ...


class Property(BaseModel):
    name: str
    value: str

    def __str__(self):
        return self.value

    def __repr__(self):
        return f'<Property {self.name}: "{self.value}">'

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)


class TroveModFile:
    index: int = 0
    offset: int = 0

    def __init__(self, cwd: Path, trove_path: Path, data: bytes):
        self.cwd = cwd
        self.trove_path = trove_path.as_posix().lower()
        self._content = BinaryReader(bytearray(data))
        self._checksum = None

    def __str__(self):
        return f'<TroveModFile "{self.trove_path} ({self.size}" bytes)>'

    def __repr__(self):
        return str(self)

    @property
    def content(self) -> BinaryReader:
        return self._content

    @content.setter
    def content(self, value: BinaryReader):
        self._content = value

    @property
    def data(self) -> bytes:
        return self.content.buffer()

    @data.setter
    def data(self, value: bytes):
        self.content = BinaryReader(bytearray(value))

    @property
    def size(self):
        return self.content.size()

    @property
    def checksum(self):
        if self._checksum is None:
            self._checksum = calculate_hash(self.padded_data)
        return self._checksum

    @property
    def padded_data(self) -> bytes:
        data = self.data
        if len(data) % 4 != 0:
            data += b"\x00" * (4 - (len(data) % 4))
        return data

    @property
    def header_format(self) -> bytes:
        data = BinaryReader(bytearray())
        data.write_int8(len(str(self.trove_path)))
        data.write_str(str(self.trove_path))
        data.extend(WriteLeb128(self.index))
        data.extend(WriteLeb128(self.offset))
        data.extend(WriteLeb128(self.size))
        data.extend(WriteLeb128(self.checksum))
        return data.buffer()


class TroveMod:
    mod_path: Path
    version: int = 1
    properties: list[Property]
    files: list[TroveModFile]
    _zip_hash: str = None
    _tmod_hash: str = None
    _zip_content: bytes = None
    _tmod_content: bytes = None
    enabled: bool = True
    name_conflicts: list[TroveMod]
    file_conflicts: list[TroveMod]
    _trovesaurus_data: Optional[Mod] = None

    def __init__(self):
        self.properties = []
        self.files = []
        self.name_conflicts = []
        self.file_conflicts = []

    def __str__(self):
        return f'<TroveMod "{self.name}">'

    def __repr__(self):
        return str(self)

    @property
    def cwd(self):
        return self.mod_path.parent

    @property
    def has_wrong_name(self):
        return self.mod_path.stem != self.name

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            new_name = self.mod_path.name.partition(".")[0] + ".tmod"
            new_path = self.cwd.joinpath(new_name)
        else:
            new_name = self.mod_path.name.partition(".")[0] + ".tmod.disabled"
            new_path = self.cwd.joinpath(new_name)
        self.mod_path.rename(new_path)
        self.mod_path = new_path

    def fix_name(self):
        suffixes = self.mod_path.suffixes
        new_mod_path = self.mod_path.with_name(self.name + "".join(suffixes))
        self.mod_path.rename(new_mod_path)
        self.mod_path = new_mod_path

    def check_conflicts(self, mods: list[TroveMod]):
        self.conflicts.clear()
        for mod in mods:
            if mod == self:
                continue
            if mod.name == self.name:
                self.name_conflicts.append(mod)
            for file in self.files:
                if file.trove_path == self.preview_path:
                    continue
                for other_file in mod.files:
                    if other_file.trove_path == mod.preview_path:
                        continue
                    if file.trove_path == other_file.trove_path:
                        self.file_conflicts.append(mod)
                        break
                if mod in self.file_conflicts:
                    break

    @property
    def conflicts(self):
        return self.name_conflicts + self.file_conflicts

    @property
    def has_conflicts(self):
        return bool(self.conflicts)

    @property
    def metadata(self) -> str:
        metadata = dict()
        metadata["name"] = self.name
        metadata["properties"] = {}
        needed_props = [
            "author",
            "title",
        ]
        for prop in needed_props:
            if prop not in [p.name for p in self.properties]:
                raise MissingPropertyError(f'Property "{prop}" is missing')
        for prop in self.properties:
            if prop.name in needed_props and not prop.value:
                raise PropertyMalformedError(f'Property "{prop.name}" has no value')
            metadata["properties"][prop.name] = prop.value
        metadata["files"] = [str(f.trove_path) for f in self.files]
        return dumps(metadata)

    @property
    def name(self):
        return self.get_property_value("title")

    @name.setter
    def name(self, value: str):
        self.add_property("title", value)

    @property
    def author(self):
        return self.get_property_value("author")

    @author.setter
    def author(self, value: str):
        self.add_property("author", value)

    @property
    def steam_id(self):
        return self.get_property_value("SteamId")

    @steam_id.setter
    def steam_id(self, value: str):
        self.add_property("SteamId", value)

    @property
    def game_version(self):
        return self.get_property_value("gameVersion")

    @game_version.setter
    def game_version(self, value: str):
        self.add_property("gameVersion", value)

    @property
    def notes(self):
        return self.get_property_value("notes")

    @notes.setter
    def notes(self, value: str):
        self.add_property("notes", value)

    @property
    def preview_path(self):
        return self.get_property_value("previewPath").lower()

    @preview_path.setter
    def preview_path(self, value: Path):
        self.add_property("previewPath", value.as_posix())

    @property
    def image(self):
        for file in self.files:
            if file.trove_path == self.preview_path:
                return base64.b64encode(file.data).decode("utf-8")
        return base64.b64encode(
            open("assets/images/construction.png", "rb").read()
        ).decode("utf-8")

    @property
    def tags(self):
        tags = self.get_property_value("tags")
        if tags:
            return tags.split(",")
        return []

    def add_tag(self, tag: str):
        tags = self.tags
        tags.append(tag)
        tags_string = ",".join(tags)
        self.add_property("tags", tags_string)

    def remove_tag(self, tag: str):
        tags = self.tags
        tags.remove(tag)
        tags_string = ",".join(tags)
        self.add_property("tags", tags_string)

    def add_property(self, name: str, value: str):
        self.remove_property(name)
        self.properties.append(Property(name=name, value=value))

    def remove_property(self, name: str):
        prop = get_attr(self.properties, name=name)
        if prop is not None:
            self.properties.remove(prop)

    def get_property(self, name: str):
        return get_attr(self.properties, name=name)

    def get_property_value(self, name: str):
        prop = self.get_property(name)
        if prop:
            return prop.value
        return None

    def reorder_files(self):
        offset = 0
        for file in self.files:
            file.index = 0
            file.offset = offset
            offset += len(file.padded_data)

    def reset_cache(self):
        self.zip_content = None
        self.zip_hash = None
        self.tmod_content = None
        self.tmod_hash = None

    def add_file(self, file: TroveModFile):
        self.files.append(file)
        self.reset_cache()
        self.reorder_files()

    def remove_file(self, file: TroveModFile):
        self.files.remove(file)
        self.reset_cache()
        self.reorder_files()

    def pre_compile(self):
        self.reorder_files()
        metadata = self.metadata
        return metadata

    def compile_zip_mod(self) -> bytes:
        if self.zip_content:
            return self.zip_content
        if not self.files:
            raise NoFilesError("No files to compile")
        metadata = self.pre_compile()
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as f:
            for file in self.files:
                f.writestr(str(file.trove_path), file.data)
            f.writestr(str("metadata.toml"), bytes(metadata, "utf-8"))
        return data.getvalue()

    def compile_tmod(self) -> bytes:
        if not self.files:
            raise NoFilesError("No files to compile")
        self.reorder_files()
        tmod = BinaryReader(bytearray())
        header_stream = BinaryReader(bytearray())
        properties_stream = BinaryReader(bytearray())
        files_list_stream = BinaryReader(bytearray())
        file_stream = BinaryReader(bytearray())
        for prop in self.properties:
            properties_stream.write_bytes(WriteLeb128(len(prop.name)))
            properties_stream.write_str(prop.name)
            properties_stream.write_bytes(WriteLeb128(len(prop.value)))
            properties_stream.write_str(prop.value)
        for file in self.files:
            file_stream.extend(bytearray(file.padded_data))
        compressor = zlib.compressobj(level=0, strategy=0, wbits=zlib.MAX_WBITS)
        chunked_file_stream = chunks(file_stream.buffer(), 32768)
        file_stream = BinaryReader(bytearray())
        for chunk in chunked_file_stream:
            file_stream.extend(bytearray(compressor.compress(chunk)))
        file_stream.extend(bytearray(compressor.flush(zlib.Z_SYNC_FLUSH)))
        for i, file in enumerate(reversed(self.files), 1):
            files_list_stream.extend(bytearray(file.header_format))
        header_stream.write_uint64(0)
        header_stream.write_uint16(self.version)
        header_stream.write_uint16(len(self.properties))
        header_stream.extend(properties_stream.buffer())
        header_stream.extend(files_list_stream.buffer())
        header_stream.seek(0)
        header_stream.write_uint64(len(header_stream.buffer()))
        tmod.extend(header_stream.buffer() + file_stream.buffer())
        return tmod.buffer()

    @property
    def zip_content(self):
        if self._zip_content is None:
            self.zip_content = self.compile_zip_mod()
        return self._zip_content

    @zip_content.setter
    def zip_content(self, value: bytes):
        self._zip_content = value

    @property
    def tmod_content(self):
        if self._tmod_content is None:
            self.tmod_content = self.compile_tmod()
        return self._tmod_content

    @tmod_content.setter
    def tmod_content(self, value: bytes):
        self._tmod_content = value

    @property
    def zip_hash(self):
        if self._zip_hash is None:
            self.zip_hash = md5(self.compile_zip_mod()).hexdigest()
        return self._zip_hash

    @zip_hash.setter
    def zip_hash(self, value: str):
        self._zip_hash = value

    @property
    def tmod_hash(self):
        if self._tmod_hash is None:
            self.tmod_hash = md5(self.compile_tmod()).hexdigest()
        return self._tmod_hash

    @tmod_hash.setter
    def tmod_hash(self, value: str):
        self._tmod_hash = value

    @property
    def trovesaurus_data(self) -> Mod:
        return self._trovesaurus_data

    @trovesaurus_data.setter
    def trovesaurus_data(self, value: Mod):
        self._trovesaurus_data = value


class TMod(TroveMod):
    def __str__(self):
        return f'<TMod "{self.name}">'

    @property
    def hash(self):
        return self.tmod_hash

    @classmethod
    def read_bytes(cls, path: Path, data: bytes):
        mod = cls()
        mod.tmod_content = data
        mod.mod_path = path
        mod.files = []
        data = BinaryReader(bytearray(data))
        header_size = data.read_uint64()
        mod.version = data.read_uint16()
        properties_count = data.read_uint16()
        mod.properties = []
        for i in range(properties_count):
            name_size = ReadLeb128(data, data.pos())
            name = data.read_str(name_size)
            value_size = ReadLeb128(data, data.pos())
            value = data.read_str(value_size)
            mod.properties.append(Property(name=name, value=value))
        file_stream = data.buffer()[header_size:]
        decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS)
        try:
            file_stream = BinaryReader(bytearray(decompressor.decompress(file_stream)))
        except:
            print("Failed to decompile mod, trying manual decompression: " + str(path))
            file_stream = BinaryReader(bytearray(mod.manual_decompression(file_stream)))
        while data.pos() < header_size:
            name_size = data.read_uint8()
            name = data.read_str(name_size)
            index = ReadLeb128(data, data.pos())
            offset = ReadLeb128(data, data.pos())
            size = ReadLeb128(data, data.pos())
            checksum = ReadLeb128(data, data.pos())
            file_stream.seek(offset)
            content = file_stream.read_bytes(size)
            file = TroveModFile(path, Path(name), content)
            file.index = index
            file.old_checksum = checksum
            mod.files.append(file)
        return mod

    def manual_decompression(self, data: bytes):
        data = BinaryReader(bytearray(data[7:-5]))
        data_chunks = data.size() // (32768 + 5)
        output = BinaryReader(bytearray())
        for i in range(data_chunks):
            output.extend(bytearray(data.read_bytes(32768)))
            data.read_bytes(5)
        output.extend(bytearray(data.read_bytes(data.size() - data.pos())))
        return output.buffer()

    def manual_compression(self, data: bytes):
        output = BinaryReader(bytearray())
        output.write_bytes(b"\x78\x01\x00\x00\x80\xFF\x7F")
        data_chunks = chunks(data, 32768)
        for data_chunk in data_chunks:
            output.write_bytes(data_chunk)
            if len(data_chunk) == 32768:
                output.write_bytes(b"\x00\x00\x80\xFF\x7F")
        output.write_bytes(b"\x00\x00\x00\xFF\xFF")
        return output.buffer()


class ZMod(TroveMod):
    def __str__(self):
        return f'<ZMod "{self.name}">'

    @property
    def hash(self):
        return self.zip_hash

    @classmethod
    def read_bytes(cls, path: Path, data: io.BytesIO):
        mod = cls()
        mod.zip_content = data.read()
        mod.mod_path = path
        mod.files = []
        with zipfile.ZipFile(data) as f:
            for file_name in f.namelist():
                if file_name.endswith("/"):
                    continue
                mod.files.append(TroveModFile(path, Path(file_name), f.read(file_name)))
        mod.name = path.stem
        return mod


class TroveModList:
    enabled: list[TroveMod]
    disabled: list[TroveMod]
    _mods: list[TroveMod]

    def __init__(self, path: Path):
        self.enabled = []
        self.disabled = []
        self._mods = []
        self.installation_path = path
        self.list_path = path.joinpath("mods")
        if self.installation_path.exists():
            self.list_path.mkdir(parents=True, exist_ok=True)
        self._populate()

    def __str__(self):
        return f'<TroveModList "{self.list_path}" count={self.count}>'

    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter(self.mods)

    def __len__(self):
        return self.count

    async def update_trovesaurus_data(self):
        hashes_query = "%23".join(self.all_hashes)
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.slynx.xyz/v1/mods/hashes?hashes={hashes_query}"
            ) as response:
                data = await response.json()
                for mod in self:
                    for k, v in data.items():
                        if mod.hash == k and v is not None:
                            mod.trovesaurus_data = Mod.parse_obj(v)
                            mod.trovesaurus_data.installed = True
                            for file in mod.trovesaurus_data.file_objs:
                                if file.hash == mod.hash:
                                    mod.trovesaurus_data.installed_file = file
                                    break
                            break

    @property
    def all_hashes(self):
        return [mod.hash for mod in self.mods]

    @property
    def name(self):
        return self.installation_path.name

    @property
    def mods(self):
        if len(self._mods) != self.count:
            self._mods = self.enabled + self.disabled
        return self._mods

    def sort_by_name(self):
        self._mods.sort(key=lambda mod: mod.name)

    @property
    def mods_with_conflicts(self):
        return [mod for mod in self.mods if mod.has_conflicts]

    @property
    def count(self):
        return len(self.enabled) + len(self.disabled)

    def refresh(self):
        self._populate()

    def _populate(self):
        self.enabled.clear()
        self.disabled.clear()
        self._populate_tmod_enabled()
        self._populate_tmod_disabled()
        self._populate_zip_enabled()
        self._populate_zip_disabled()
        self.sort_by_name()
        for mod in self.mods:
            mod.check_conflicts(self.mods)

    def _populate_tmod_enabled(self):
        for file in self.list_path.glob("*.tmod"):
            file_data = file.read_bytes()
            mod = TMod.read_bytes(file, file_data)
            if mod.has_wrong_name:
                mod.fix_name()
            self.enabled.append(mod)

    def _populate_tmod_disabled(self):
        for file in self.list_path.glob("*.tmod.disabled"):
            file_data = file.read_bytes()
            mod = TMod.read_bytes(file, file_data)
            if mod.has_wrong_name:
                mod.fix_name()
            mod.enabled = False
            self.disabled.append(mod)

    def _populate_zip_enabled(self):
        for file in self.list_path.glob("*.zip"):
            file_data = file.read_bytes()
            mod = ZMod.read_bytes(file, BytesIO(file_data))
            self.enabled.append(mod)

    def _populate_zip_disabled(self):
        for file in self.list_path.glob("*.zip.disabled"):
            file_data = file.read_bytes()
            mod = ZMod.read_bytes(file, BytesIO(file_data))
            mod.enabled = False
            self.disabled.append(mod)


class TPack:
    properties: list[Property]
    files: list[TroveMod]

    def __init__(self):
        self.properties = []
        self.files = []

    def compile(self):
        pack = BinaryReader(bytearray())
        file_stream = BinaryReader(bytearray())
        pack.write_uint64(0)
        pack.write_uint16(1)
        pack.write_uint16(len(self.properties))
        for prop in self.properties:
            pack.write_bytes(WriteLeb128(len(prop.name)))
            pack.write_str(prop.name)
            pack.write_bytes(WriteLeb128(len(prop.value)))
            pack.write_str(prop.value)
        offset = 0
        for file in self.files:
            mod_data = file.mod_path.read_bytes()
            pack.write_int8(len(file.mod_path.name))
            pack.write_str(file.mod_path.name)
            pack.write_bytes(WriteLeb128(0))
            pack.write_bytes(WriteLeb128(0))
            pack.write_bytes(WriteLeb128(offset))
            pack.write_bytes(WriteLeb128(len(mod_data)))
            pack.write_bytes(WriteLeb128(calculate_hash(mod_data)))
            offset += len(mod_data)
            file_stream.write_bytes(mod_data)
        pack.seek(0)
        pack.write_uint64(pack.size())
        compressor = zlib.compressobj(level=0, strategy=0, wbits=zlib.MAX_WBITS)
        chunked_file_stream = chunks(file_stream.buffer(), 32768)
        file_stream = BinaryReader(bytearray())
        for chunk in chunked_file_stream:
            file_stream.extend(bytearray(compressor.compress(chunk)))
        file_stream.extend(bytearray(compressor.flush(zlib.Z_SYNC_FLUSH)))
        pack.extend(file_stream.buffer())
        return pack.buffer()

    @classmethod
    def parse(cls, path: Path, data):
        tpack = cls()
        pack = BinaryReader(bytearray(data))
        header_size = pack.read_uint64()
        version = pack.read_uint16()
        file_count = pack.read_uint16()
        property_count = pack.read_uint16()
        for _ in range(property_count):
            name_length = ReadLeb128(pack)
            name = pack.read_str(name_length)
            value_length = ReadLeb128(pack)
            value = pack.read_str(value_length)
            tpack.add_property(name, value)
        for _ in range(file_count):
            file_name_length = pack.read_int8()
            file_name = pack.read_str(file_name_length)
            index = ReadLeb128(pack, pack.pos())
            file_offset = ReadLeb128(pack, pack.pos())
            file_size = ReadLeb128(pack, pack.pos())
            file_hash = ReadLeb128(pack, pack.pos())
            tpack.files.append(TroveMod(file_name, file_offset, file_size, file_hash))

    @property
    def author(self):
        return self.get_property("author").value

    @author.setter
    def author(self, value):
        self.add_property("author", value)

    def get_property(self, name):
        return get_attr(self.properties, name=name)

    def add_property(self, name, value):
        if self.get_property(name) is not None:
            self.remove_property(name)
        self.properties.append(Property(name=name, value=value))

    def remove_property(self, name):
        self.properties.remove(self.get_property(name))


class ModEntry(Document):
    hash: Indexed(str, unique=True)
    mod_id: Optional[int] = None
    name: str
    format: str
    authors: list[ModAuthor]
    description: Optional[str] = None


class SearchMod(Document):
    id: Indexed(int)
    name: Indexed(str)
    type: Indexed(str)
    sub_type: Indexed(str)
    views: int
    downloads: int
    likes: int
    authors: list[str]
    last_update: int
    hot: int
