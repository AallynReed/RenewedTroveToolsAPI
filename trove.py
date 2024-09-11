from datetime import datetime, timedelta, UTC


class TroveTime:
    @property
    def now(self):
        return (datetime.now(UTC) - timedelta(hours=11)).replace(microsecond=0)

    def get_luxion_rotations(self):
        first = datetime(2017, 12, 15, 11, tzinfo=UTC)
        elapsed = (self.now - first).total_seconds()
        length = 60 * 60 * 24 * 3  # 3 days
        cycle = 60 * 60 * 24 * 14  # 14 days
        completed = int(elapsed // cycle)
        luxion_rotations = {}
        luxion_rotations["history"] = [
            {
                "index": i,
                "start": int(first.timestamp() + cycle * i),
                "end": int(first.timestamp() + cycle * i + length),
            }
            for i in range(completed)
        ]

        luxion_rotations["current"] = {
            "index": completed,
            "start": int(first.timestamp() + cycle * completed),
            "end": int(first.timestamp() + cycle * completed + length),
        }

        luxion_rotations["next"] = {
            "index": completed + 1,
            "start": int(first.timestamp() + cycle * (completed + 1)),
            "end": int(first.timestamp() + cycle * (completed + 1) + length),
        }
        return luxion_rotations

    def get_corruxion_rotations(self):
        first = datetime(2020, 12, 4, 11, tzinfo=UTC)
        elapsed = (self.now - first).total_seconds()
        length = 60 * 60 * 24 * 3  # 3 days
        cycle = 60 * 60 * 24 * 14  # 14 days
        completed = int(elapsed // cycle)
        corruxion_rotations = {}
        corruxion_rotations["history"] = [
            {
                "index": i,
                "start": int(first.timestamp() + cycle * i),
                "end": int(first.timestamp() + cycle * i + length),
            }
            for i in range(completed)
        ]

        corruxion_rotations["current"] = {
            "index": completed,
            "start": int(first.timestamp() + cycle * completed),
            "end": int(first.timestamp() + cycle * completed + length),
        }

        corruxion_rotations["next"] = {
            "index": completed + 1,
            "start": int(first.timestamp() + cycle * (completed + 1)),
            "end": int(first.timestamp() + cycle * (completed + 1) + length),
        }
        return corruxion_rotations

    def get_fluxion_rotations(self):
        first = datetime(2023, 7, 18, 11, tzinfo=UTC)
        elapsed = (self.now - first).total_seconds()
        length = 60 * 60 * 24 * 3  # 3 days
        split = 60 * 60 * 24 * 7  # 7 days
        cycle = 60 * 60 * 24 * 14  # 14 days
        completed = int(elapsed // cycle)
        fluxion_rotations = {}
        fluxion_rotations["history"] = [
            {
                "index": i,
                "vote_phase": {
                    "start": int(first.timestamp() + cycle * i),
                    "end": int(first.timestamp() + cycle * i + length),
                },
                "buy_phase": {
                    "start": int(first.timestamp() + cycle * i + split),
                    "end": int(first.timestamp() + cycle * i + length + split),
                },
            }
            for i in range(completed)
        ]

        fluxion_rotations["current"] = {
            "index": completed,
            "vote_phase": {
                "start": int(first.timestamp() + cycle * completed),
                "end": int(first.timestamp() + cycle * completed + length),
            },
            "buy_phase": {
                "start": int(first.timestamp() + cycle * completed + split),
                "end": int(first.timestamp() + cycle * completed + length + split),
            },
        }

        fluxion_rotations["next"] = {
            "index": completed + 1,
            "vote_phase": {
                "start": int(first.timestamp() + cycle * (completed + 1)),
                "end": int(first.timestamp() + cycle * (completed + 1) + length),
            },
            "buy_phase": {
                "start": int(first.timestamp() + cycle * (completed + 1) + split),
                "end": int(
                    first.timestamp() + cycle * (completed + 1) + length + split
                ),
            },
        }
        return fluxion_rotations
