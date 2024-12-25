import datetime
import re
from typing import Final

import pytz

SUNDAY_DAY_OF_WEEK: Final[int] = 6

DATE_FMT: Final[str] = "%m%d%y"

OR_PATTERN: Final[re.Pattern] = re.compile("OR[:]?$", re.IGNORECASE)

DEFAULT_TIMEZONE: Final[datetime.tzinfo] = pytz.timezone("America/New_York")

READING_TITLE_FMT: Final[str] = "A reading from the {TITLE}"
DAILY_READING_DEFAULT_MSS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}.cfm"
DAILY_READING_DAWN_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-Dawn.cfm"
DAILY_READING_DAY_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-Day.cfm"
DAILY_READING_NIGHT_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-Night.cfm"
DAILY_READING_VIGIL_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-Vigil.cfm"
DAILY_READING_YEAR_A_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-YearA.cfm"
DAILY_READING_YEAR_B_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-YearB.cfm"
DAILY_READING_YEAR_C_MASS_URL_FMT: Final[str] = "https://bible.usccb.org/bible/readings/{DATE:%m%d%y}-YearC.cfm"

READING_CLOSE_REMARKS: Final[str] = "The word of the Lord."
READING_CLOSE_RESPONSE: Final[str] = "Thanks be to God."
GOSPEL_CLOSE_RESPONSE: Final[str] = "Praise to you, Lord Jesus Christ."
GOSPEL_CLOSE_REMARKS: Final[str] = "The Gospel of the Lord."

SECTION_HEADER_FIRST_READING: Final[str] = "First Reading"
SECTION_HEADER_SECOND_READING: Final[str] = "Second Reading"
SECTION_HEADER_THIRD_READING: Final[str] = "Third Reading"
SECTION_HEADER_FORTH_READING: Final[str] = "Forth Reading"
SECTION_HEADER_READINGS: Final[dict[int, str]] = {
    1: SECTION_HEADER_FIRST_READING,
    2: SECTION_HEADER_SECOND_READING,
    3: SECTION_HEADER_THIRD_READING,
    4: SECTION_HEADER_FORTH_READING,
}

OLD_TESTAMENT_BOOKS: Final[list[dict[str, str]]] = [
    {"short_abbreviation": "Gn", "long_abbreviation": "Gen", "name": "Genesis", "title": "Book of Genesis"},
    {"short_abbreviation": "Ex", "long_abbreviation": "Exod", "name": "Exodus", "title": "Book of Exodus"},
    {"short_abbreviation": "Lv", "long_abbreviation": "Lev", "name": "Leviticus", "title": "Book of Leviticus"},
    {"short_abbreviation": "Nm", "long_abbreviation": "Num", "name": "Numbers", "title": "Book of Numbers"},
    {"short_abbreviation": "Dt", "long_abbreviation": "Deut", "name": "Deuteronomy", "title": "Book of Deuteronomy"},
    {"short_abbreviation": "Jos", "long_abbreviation": "Josh", "name": "Joshua", "title": "Book of Joshua"},
    {"short_abbreviation": "Jgs", "long_abbreviation": "Judg", "name": "Judges", "title": "Book of Judges"},
    {"short_abbreviation": "Ru", "long_abbreviation": "Ruth", "name": "Ruth", "title": "Book of Ruth"},
    {"short_abbreviation": "1Sm", "long_abbreviation": "1Sam", "name": "1 Samuel", "title": "First Book of Samuel"},
    {"short_abbreviation": "2Sm", "long_abbreviation": "2Sam", "name": "2 Samuel", "title": "Second Book of Samuel"},
    {"short_abbreviation": "1K", "long_abbreviation": "1Kgs", "name": "1 Kings", "title": "First Book of Kings"},
    {"short_abbreviation": "2K", "long_abbreviation": "2Kgs", "name": "2 Kings", "title": "Second Book of Kings"},
    {
        "short_abbreviation": "1Chr",
        "long_abbreviation": "1Chr",
        "name": "1 Chronicles",
        "title": "First Book of Chronicles",
    },
    {
        "short_abbreviation": "2Chr",
        "long_abbreviation": "2Chr",
        "name": "2 Chronicles",
        "title": "Second Book of Chronicles",
    },
    {"short_abbreviation": "Ezr", "long_abbreviation": "Ezra", "name": "Ezra", "title": "Book of Ezra"},
    {"short_abbreviation": "Ne", "long_abbreviation": "Neh", "name": "Nehemiah", "title": "Book of Nehemiah"},
    {"short_abbreviation": "Tb", "long_abbreviation": "Tob", "name": "Tobit", "title": "Book of Tobit"},
    {"short_abbreviation": "Jd", "long_abbreviation": "Jdt", "name": "Judith", "title": "Book of Judith"},
    {"short_abbreviation": "Es", "long_abbreviation": "Est", "name": "Esther", "title": "Book of Esther"},
    {
        "short_abbreviation": "1Mc",
        "long_abbreviation": "1Mac",
        "name": "1 Maccabees",
        "title": "First Book of Maccabees",
    },
    {
        "short_abbreviation": "2Mc",
        "long_abbreviation": "2Mac",
        "name": "2 Maccabees",
        "title": "Second Book of Maccabees",
    },
    {"short_abbreviation": "Jb", "long_abbreviation": "Job", "name": "Job", "title": "Book of Job"},
    {"short_abbreviation": "Ps", "long_abbreviation": "Psalms", "name": "Psalms", "title": "Book of Psalms"},
    {"short_abbreviation": "Pr", "long_abbreviation": "Prv", "name": "Proverbs", "title": "Book of Proverbs"},
    {"short_abbreviation": "Ec", "long_abbreviation": "Eccl", "name": "Ecclesiastes", "title": "Book of Ecclesiastes"},
    {"short_abbreviation": "Sg", "long_abbreviation": "Song", "name": "Song of Songs", "title": "Song of Songs"},
    {"short_abbreviation": "Ws", "long_abbreviation": "Wis", "name": "Wisdom", "title": "Book of Wisdom"},
    {"short_abbreviation": "Si", "long_abbreviation": "Sir", "name": "Sirach", "title": "Book of Sirach"},
    {"short_abbreviation": "Is", "long_abbreviation": "Isa", "name": "Isaiah", "title": "Book of the Prophet Isaiah"},
    {
        "short_abbreviation": "Jr",
        "long_abbreviation": "Jer",
        "name": "Jeremiah",
        "title": "Book of the Prophet Jeremiah",
    },
    {"short_abbreviation": "Lm", "long_abbreviation": "Lam", "name": "Lamentations", "title": "Book of Lamentations"},
    {"short_abbreviation": "Ba", "long_abbreviation": "Bar", "name": "Baruch", "title": "Book of Baruch"},
    {
        "short_abbreviation": "Ez",
        "long_abbreviation": "Ezek",
        "name": "Ezekiel",
        "title": "Book of the Prophet Ezekiel",
    },
    {"short_abbreviation": "Dn", "long_abbreviation": "Dan", "name": "Daniel", "title": "Book of the Prophet Daniel"},
    {"short_abbreviation": "Ho", "long_abbreviation": "Hos", "name": "Hosea", "title": "Book of the Prophet Hosea"},
    {"short_abbreviation": "Jl", "long_abbreviation": "Joel", "name": "Joel", "title": "Book of the Prophet Joel"},
    {"short_abbreviation": "Am", "long_abbreviation": "Amos", "name": "Amos", "title": "Book of the Prophet Amos"},
    {
        "short_abbreviation": "Ob",
        "long_abbreviation": "Obad",
        "name": "Obadiah",
        "title": "Book of the Prophet Obadiah",
    },
    {"short_abbreviation": "Jon", "long_abbreviation": "Jonah", "name": "Jonah", "title": "Book of the Prophet Jonah"},
    {"short_abbreviation": "Mi", "long_abbreviation": "Mic", "name": "Micah", "title": "Book of the Prophet Micah"},
    {"short_abbreviation": "Na", "long_abbreviation": "Nah", "name": "Nahum", "title": "Book of the Prophet Nahum"},
    {
        "short_abbreviation": "Hb",
        "long_abbreviation": "Hab",
        "name": "Habakkuk",
        "title": "Book of the Prophet Habakkuk",
    },
    {
        "short_abbreviation": "Zp",
        "long_abbreviation": "Zep",
        "name": "Zephaniah",
        "title": "Book of the Prophet Zephaniah",
    },
    {"short_abbreviation": "Ghg", "long_abbreviation": "Hag", "name": "Haggai", "title": "Book of the Prophet Haggai"},
    {
        "short_abbreviation": "Zc",
        "long_abbreviation": "Zec",
        "name": "Zechariah",
        "title": "Book of the Prophet Zechariah",
    },
    {"short_abbreviation": "Ml", "long_abbreviation": "Mal", "name": "Malachi", "title": "Book of the Prophet Malachi"},
]

NEW_TESTAMENT_BOOKS: Final[list[dict[str, str]]] = [
    {
        "short_abbreviation": "Mt",
        "long_abbreviation": "Matt",
        "name": "Matthew",
        "title": "holy Gospel according to Matthew",
    },
    {"short_abbreviation": "Mk", "long_abbreviation": "Mark", "name": "Mark", "title": "holy Gospel according to Mark"},
    {"short_abbreviation": "Lk", "long_abbreviation": "Luke", "name": "Luke", "title": "holy Gospel according to Luke"},
    {"short_abbreviation": "Jn", "long_abbreviation": "John", "name": "John", "title": "holy Gospel according to John"},
    {"short_abbreviation": "Ac", "long_abbreviation": "Acts", "name": "Acts", "title": "Acts of the Apostles"},
    {
        "short_abbreviation": "Rm",
        "long_abbreviation": "Rom",
        "name": "Romans",
        "title": "Letter of Saint Paul to the Romans",
    },
    {
        "short_abbreviation": "1C",
        "long_abbreviation": "1Cor",
        "name": "1 Corinthians",
        "title": "First Letter of Saint Paul to the Corinthians",
    },
    {
        "short_abbreviation": "2C",
        "long_abbreviation": "2Cor",
        "name": "2 Corinthians",
        "title": "Second Letter of Saint Paul to the Corinthians",
    },
    {
        "short_abbreviation": "Ga",
        "long_abbreviation": "Gal",
        "name": "Galatians",
        "title": "Letter of Saint Paul to the Galatians",
    },
    {
        "short_abbreviation": "Ep",
        "long_abbreviation": "Eph",
        "name": "Ephesians",
        "title": "Letter of Saint Paul to the Ephesians",
    },
    {
        "short_abbreviation": "Ph",
        "long_abbreviation": "Phil",
        "name": "Philippians",
        "title": "Letter of Saint Paul to the Philippians",
    },
    {
        "short_abbreviation": "Cl",
        "long_abbreviation": "Col",
        "name": "Colossians",
        "title": "Letter of Saint Paul to the Colossians",
    },
    {
        "short_abbreviation": "1Th",
        "long_abbreviation": "1Thes",
        "name": "1 Thessalonians",
        "title": "First Letter of Saint Paul to the Thessalonians",
    },
    {
        "short_abbreviation": "2Th",
        "long_abbreviation": "2Thes",
        "name": "2 Thessalonians",
        "title": "Second Letter of Saint Paul to the Thessalonians",
    },
    {
        "short_abbreviation": "1Tm",
        "long_abbreviation": "1Tim",
        "name": "1 Timothy",
        "title": "First Letter of Saint Paul to Timothy",
    },
    {
        "short_abbreviation": "2Tm",
        "long_abbreviation": "2Tim",
        "name": "2 Timothy",
        "title": "Second Letter of Saint Paul to Timothy",
    },
    {"short_abbreviation": "Ti", "long_abbreviation": "Tit", "name": "Titus", "title": "Letter of Saint Paul to Titus"},
    {
        "short_abbreviation": "Phlm",
        "long_abbreviation": "Philem",
        "name": "Philemon",
        "title": "Letter of Saint Paul to Philemon",
    },
    {"short_abbreviation": "He", "long_abbreviation": "Heb", "name": "Hebrews", "title": "Letter to the Hebrews"},
    {"short_abbreviation": "Jas", "long_abbreviation": "James", "name": "James", "title": "Letter of Saint James"},
    {
        "short_abbreviation": "1Pt",
        "long_abbreviation": "1Pet",
        "name": "1 Peter",
        "title": "First Letter of Saint Peter",
    },
    {
        "short_abbreviation": "2Pt",
        "long_abbreviation": "2Pet",
        "name": "2 Peter",
        "title": "Second Letter of Saint Peter",
    },
    {
        "short_abbreviation": "1Jn",
        "long_abbreviation": "1John",
        "name": "1 John",
        "title": "First Letter of Saint John",
    },
    {
        "short_abbreviation": "2Jn",
        "long_abbreviation": "2John",
        "name": "2 John",
        "title": "Second Letter of Saint John",
    },
    {
        "short_abbreviation": "3Jn",
        "long_abbreviation": "3John",
        "name": "3 John",
        "title": "Third Letter of Saint John",
    },
    {"short_abbreviation": "Jd", "long_abbreviation": "Jude", "name": "Jude", "title": "Letter of Saint Jude"},
    {"short_abbreviation": "Rv", "long_abbreviation": "Rev", "name": "Revelation", "title": "Book of Revelation"},
]
