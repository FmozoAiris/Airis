
import re

RECORD_DATA_LENGTH = 254  
FILE_ENCODING = "cp1252"


class A3Record:

    def __init__(self, company_code, date, record_type):
        self._chars = [" "] * RECORD_DATA_LENGTH
        self.set(1, 1, "4")
        self.set(2, 5, str(company_code or "").strip().zfill(5)[-5:])
        self.set(7, 8, fmt_date(date))
        self.set(15, 1, record_type)
        self.set(253, 1, "E")  
        self.set(254, 1, "N")  

    def set(self, position, length, value):
        value = fmt_text(value, length)
        start = position - 1
        self._chars[start : start + length] = list(value)

    def render(self):
        line = "".join(self._chars)
        assert len(line) == RECORD_DATA_LENGTH, len(line)
        return line + "\r\n"


def _sanitize(value):
    value = "" if value is None or value is False else str(value)
    value = value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return value.encode(FILE_ENCODING, errors="replace").decode(FILE_ENCODING)


def fmt_text(value, length):
    return _sanitize(value)[:length].ljust(length)


def fmt_amount(value):
    value = round(float(value or 0.0), 2)
    sign = "-" if value < 0 else "+"
    body = "%013.2f" % abs(value)
    if len(body) > 13:
        raise ValueError("Importe demasiado grande para A3: %s" % value)
    return sign + body


def fmt_rate(value):
    value = abs(round(float(value or 0.0), 2))
    if value >= 100:
        raise ValueError("Porcentaje no válido para A3: %s" % value)
    return "%05.2f" % value


def fmt_date(value):
    return value.strftime("%Y%m%d") if value else " " * 8


def fmt_account(code, length):
    code = "".join(ch for ch in str(code or "") if ch.isalnum())
    if not code:
        return ""
    if len(code) < length:
        code = code.ljust(length, "0")
    return code[:12]


def fmt_vat(vat):
    vat = "".join(ch for ch in str(vat or "") if ch.isalnum()).upper()
    if vat.startswith("ES"):
        vat = vat[2:]
    return vat


def fmt_number(value, length=10):
    value = str(value or "").strip()
    if len(value) <= length:
        return value
    parts = [part for part in re.split(r"[^0-9A-Za-z]+", value) if part]
    if len(parts) >= 2 and parts[-1].isdigit():
        sequence = parts[-1].lstrip("0") or "0"
        head = "".join(
            part[-2:] if part.isdigit() and len(part) == 4 else part
            for part in parts[:-1]
        )
        room = length - len(head)
        if room >= len(sequence):
            return head + sequence.zfill(room)
    return "".join(parts)[-length:]
