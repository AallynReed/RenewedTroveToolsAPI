from PIL import Image, ImageDraw, ImageColor, ImageFont
import re


class Ally:
    def __init__(self, data: dict):
        self._data = data

    @property
    def name(self):
        return self._data["name"]

    @property
    def qualified_name(self):
        return self._data["filename"].split("/")[-1]

    @property
    def description(self):
        return self._data["desc"]

    @property
    def category(self):
        return self._data["category"]

    @property
    def designer(self):
        return self._data["designer"]

    @property
    def power(self):
        return int(self._data["powerrank"])

    @property
    def mastery(self):
        value = int(self._data["mastery"])
        return value if value > 0 else 0

    @property
    def geode_mastery(self):
        value = int(self._data["mastery_geode"])
        return value if value > 0 else 0

    @property
    def stats(self):
        return self._get_stats()

    @property
    def abilities(self):
        return self._get_abilities()

    def _get_abilities(self):
        abilities = []
        find = re.findall(
            "(?i)<p>([0-9a-z %.,]+)</p>", self._data["tooltip"], re.MULTILINE
        )
        if find:
            for ability in find:
                if ability == "Ally":
                    continue
                abilities.append(ability)
        return abilities

    def _get_stats(self):
        stats = {}
        results = re.findall(
            r"(?i)<li>(-?[0-9.]+%?) ([a-z ]+)<\/li>", self._data["tooltip"]
        )
        for result in results:
            value = self._fix_value(result[0])
            stats[result[1]] = value
        return stats

    def _fix_value(self, text):
        if "%" in text:
            return text
        elif "." in text:
            return float(text)
        return int(text)


class Tooltip:
    def __init__(self, data: Ally):
        self.data = data
        self._setup_fonts()
        self._setup_ratios()
        self.output = Image.new(
            "RGBA", (self.width, self.height), (0, 0, 0, int(255 * 0.8))
        )
        self.draw = ImageDraw.Draw(self.output)
        self.indentation = 73

    def indent(self, value: int = 60):
        self.indentation += value

    def _draw_header(self, value):
        x1 = int(self.width * (2.5 / self.owidth))
        y1 = 6
        x2 = x1 + (self.width * (355 / self.owidth))
        y2 = y1 + 64
        self.draw.rectangle(((x1, y1), (x2, y2)), fill=ImageColor.getrgb("#033444"))

        left = int(self.width * (6 / self.owidth))
        top = 7
        self.draw.text((left, top), value, font=self.headerfont)

    def _draw_power_rank(self, value):
        if not value:
            return
        w = self.draw.textlength(f"POWER RANK {value}", font=self.powerfont)
        left = int((self.width - w) / 2)
        self.draw.text(
            (left, self.indentation),
            f"POWER RANK {value}",
            ImageColor.getrgb("#d1c854"),
            font=self.powerfont,
        )
        self.indent()

    def _draw_ally(self):
        left = int(self.width * (6 / self.owidth))
        self.draw.text((left, self.indentation), "Ally", font=self.allyfont)
        self.indent()

    def _draw_stats(self, values):
        if not values:
            return
        for name, value in values.items():
            w = self.draw.textlength(str(value), font=self.powerfont)
            left = int(self.width * (46 / self.owidth)) - int(w)
            self.draw.text(
                (left, self.indentation),
                str(value),
                ImageColor.getrgb("#a2984d"),
                font=self.powerfont,
            )
            left = int(self.width * (56 / self.owidth))
            self.draw.text(
                (left, self.indentation),
                name,
                ImageColor.getrgb("#a2984d"),
                font=self.powerfont,
            )
            self.indent()

    def _draw_abilities(self, values):
        if not values:
            return
        split_abilities = []
        for ability in values:
            split_abilities.extend(
                self._text_wrap(
                    ability, self.abilityfont, (self.width * (350 / self.owidth))
                )
            )
        for abi in split_abilities:
            left = int(self.width * (6 / self.owidth))
            self.draw.text(
                (left, self.indentation),
                abi,
                ImageColor.getrgb("#fb6a2e"),
                font=self.abilityfont,
            )
            self.indent()

    def _draw_description(self, value):
        if not value:
            return
        lines = []
        for line in value.split("\n"):
            lines.extend(
                self._text_wrap(line, self.allyfont, (self.width * (345 / self.owidth)))
            )
        for line in lines:
            if not line:
                continue
            left = int(self.width * (6 / self.owidth))
            self.draw.text(
                (left, self.indentation),
                line,
                ImageColor.getrgb("#c2c56d"),
                font=self.allyfont,
            )
            self.indent()

    def _draw_mastery(self, value):
        if not value:
            return
        left = int(self.width * (6 / self.owidth))
        self.draw.text(
            (left, self.indentation),
            f"{value} Mastery Points",
            ImageColor.getrgb("#eeee00"),
            font=self.abilityfont,
        )
        self.indent()

    def _draw_geode_mastery(self, value):
        if not value:
            return
        left = int(self.width * (6 / self.owidth))
        self.draw.text(
            (left, self.indentation),
            f"{value} Geode Mastery Points",
            ImageColor.getrgb("#00ffff"),
            font=self.abilityfont,
        )
        self.indent()

    def _draw_designer(self, value):
        if not value and value == "Trove Team":
            return
        w = self.draw.textlength("Designed by:", font=self.designfont)
        left = int(self.width * (354 / self.owidth)) - w
        self.draw.text((left, self.indentation), "Designed by:", font=self.designfont)
        self.indent(40)
        w = self.draw.textlength(value, font=self.designerfont)
        left = int(self.width * (354 / self.owidth)) - w
        self.draw.text((left, self.indentation), value, font=self.designerfont)

    def generate_image(self):
        self._draw_header(self.data.name)
        self._draw_power_rank(self.data.power)
        self._draw_ally()
        self._draw_stats(self.data.stats)
        self._draw_abilities(self.data.abilities)
        self._draw_description(self.data.description)
        self._draw_mastery(self.data.mastery)
        self._draw_geode_mastery(self.data.geode_mastery)
        self._draw_designer(self.data.designer)
        return self.output

    def _setup_ratios(self):
        self.oheight = 202
        self.owidth = 360
        self.width = 1080
        self.height = self._check_height_add()

    def _setup_fonts(self):
        self.font_location = "website/assets/fonts/OpenSans.ttf"
        self.headerfont = ImageFont.truetype(self.font_location, 43, encoding="utf-8")
        self.powerfont = ImageFont.truetype(self.font_location, 38, encoding="utf-8")
        self.allyfont = ImageFont.truetype(self.font_location, 36, encoding="utf-8")
        self.abilityfont = ImageFont.truetype(self.font_location, 37, encoding="utf-8")
        self.designfont = ImageFont.truetype(self.font_location, 30, encoding="utf-8")
        self.designerfont = ImageFont.truetype(self.font_location, 40, encoding="utf-8")

    def _check_height_add(self):
        add = 60
        height = 73 + add
        if self.data.power:
            height += add
        if self.data.stats:
            height += add * len(self.data.stats.keys())
        if self.data.abilities:
            abilities = []
            for abi in self.data.abilities:
                abilities.extend(
                    self._text_wrap(
                        abi, self.abilityfont, (self.width * (350 / self.owidth))
                    )
                )
            height += add * len(abilities)
        if self.data.description:
            lines = []
            for line in self.data.description.split("\n"):
                lines.extend(
                    self._text_wrap(
                        line, self.allyfont, (self.width * (345 / self.owidth))
                    )
                )
            height += add * len([l for l in lines if l])
        if self.data.mastery:
            height += add
        if self.data.geode_mastery:
            height += add
        if self.data.designer and self.data.designer != "Trove Team":
            height += int(add * 1.7)
        return height

    def _text_wrap(self, text, font, max_width):
        lines = []
        if font.getlength(text) <= max_width:
            lines.append(text)
        else:
            words = text.split(" ")
            i = 0
            while i < len(words):
                line = ""
                while i < len(words) and font.getlength(line + words[i]) <= max_width:
                    line = line + words[i] + " "
                    i += 1
                if not line:
                    line = words[i]
                    i += 1
                lines.append(line)
        return lines
