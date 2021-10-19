

# PE Resource Types
resource_types = (
    (1, 'RT_CURSOR'),
    (2, 'RT_BITMAP'),
    (3, 'RT_ICON'),
    (4, 'RT_MENU'),
    (5, 'RT_DIALOG'),
    (6, 'RT_STRING'),
    (7, 'RT_FONTDIR'),
    (8, 'RT_FONT'),
    (9, 'RT_ACCELERATOR'),
    (10, 'RT_RCDATA'),
    (11, 'RT_MESSAGETABLE'),
    (12, 'RT_GROUP_CURSOR'),
    (14, 'RT_GROUP_ICON'),
    (16, 'RT_VERSION'),
    (17, 'RT_DLGINCLUDE'),
    (19, 'RT_PLUGPLAY'),
    (20, 'RT_VXD'),
    (21, 'RT_ANICURSOR'),
    (22, 'RT_ANIICON'),
    (23, 'RT_HTML'),
    (24, 'RT_MANIFEST'),
)

def getRsrcTypes():
    return resource_types

# Language identifier constants and strings
# https://docs.microsoft.com/en-us/windows/desktop/intl/language-identifier-constants-and-strings#language-identifier-notes
langcodes = (
    (0x0C00, 'custom default'),  # Default custom locale language-Default custom sublanguage'
    (0x1400, 'ui_custom_default'),  # Default custom MUI locale language-Default custom MUI sublanguage
    (0x007f, 'invariant'),  # Invariant locale language-invariant sublanguage
    (0x0000, 'neutral'),  # Neutral locale language-Neutral sublanguage
    (0x0800, 'sys default'),  # System default locale language-System default sublanguage
    (0x1000, 'custom unspecified'),  # Unspecified custom locale language-Unspecified custom sublanguage
    (0x0400, 'default'),  # User default locale language-User default sublanguage
    (0x0436, 'af-ZA'),  # AFRIKAANS_SOUTH_AFRICA
    (0x041C, 'sq-AL'),  # ALBANIAN_ALBANIA
    (0x0484, 'gsw-FR'),  # ALSATIAN_FRANCE
    (0x045E, 'am-ET'),  # AMHARIC_ETHIOPIA
    (0x1401, 'ar-DZ'),  # ARABIC_ALGERIA
    (0x3C01, 'ar-BH'),  # ARABIC_BAHRAIN
    (0x0C01, 'ar-EG'),  # ARABIC_EGYPT
    (0x0801, 'ar-IQ'),  # ARABIC_IRAQ
    (0x2C01, 'ar-JO'),  # ARABIC_JORDAN
    (0x3401, 'ar-KW'),  # ARABIC_KUWAIT
    (0x3001, 'ar-LB'),  # ARABIC_LEBANON
    (0x1001, 'ar-LY'),  # ARABIC_LIBYA
    (0x1801, 'ar-MA'),  # ARABIC_MOROCCO
    (0x2001, 'ar-OM'),  # ARABIC_OMAN
    (0x4001, 'ar-QA'),  # ARABIC_QATAR
    (0x0401, 'ar-SA'),  # ARABIC_SAUDI_ARABIA
    (0x2801, 'ar-SY'),  # ARABIC_SYRIA
    (0x1C01, 'ar-TN'),  # ARABIC_TUNISIA
    (0x3801, 'ar-AE'),  # ARABIC_UAE
    (0x2401, 'ar-YE'),  # ARABIC_YEMEN
    (0x042B, 'hy-AM'),  # ARMENIAN_ARMENIA
    (0x044D, 'as-IN'),  # ASSAMESE_INDIA
    (0x082C, 'az-AZ-Cyrillic'),  # AZERI_CYRILLIC
    (0x042C, 'az-AZ-Latin'),  # AZERI_LATIN
    (0x0445, 'bn-Bangledesh'),  # BANGLA_BANGLADESH AND BANGLA_INDIA
    (0x0845, 'bn-IN'),  # BANGLA_INDIA
    (0x046D, 'ba-RU'),  # BASHKIR_RUSSIA
    (0x042D, 'Basque-Basque'),  # BASQUE_BASQUE
    (0x0423, 'be-BY'),  # BELARUSIAN_BELARUS
    (0x781A, 'bs-neutral'),  # BOSNIAN NEUTRAL
    (0x201A, 'bs-BA-Cyrillic'),  # BOSNIAN_BOSNIA_HERZEGOVINA_CYRILLIC
    (0x141A, 'bs-BA-Latin'),  # BOSNIAN_BOSNIA_HERZEGOVINA_LATIN
    (0x047E, 'br-FR'),  # BRETON_FRANCE
    (0x0402, 'bg-BG'),  # BULGARIAN_BULGARIA
    (0x0492, 'ku-IQ'),  # CENTRAL_KURDISH_IRAQ
    (0x045C, 'chr-Cher'),  # CHEROKEE_CHEROKEE
    (0x0403, 'ca-ES'),  # CATALAN_CATALAN
    (0x0C04, 'zh-HK'),  # CHINESE_HONGKONG
    (0x1404, 'zh-MO'),  # CHINESE_MACAU
    (0x1004, 'zh-SG'),  # CHINESE_SINGAPORE
    (0x0004, 'zh-Hans'),  # CHINESE_SIMPLIFIED
    (0x7C04, 'zh-Hant'),  # CHINESE_TRADITIONAL
    (0x0483, 'co-FR'),  # CORSICAN_FRANCE
    (0x001A, 'hr'),  # CROATIAN Neutral
    (0x101A, 'hr-BA'),  # CROATIAN_BOSNIA_HERZEGOVINA_LATIN
    (0x041A, 'hr-HR'),  # CROATIAN_CROATIA
    (0x0405, 'cs-CZ'),  # CZECH_CZECH_REPUBLIC
    (0x0406, 'da-DK'),  # DANISH_DENMARK
    (0x048C, 'prs-AF'),  # DARI_AFGHANISTAN
    (0x0465, 'dv-MV'),  # DIVEHI_MALDIVES
    (0x0813, 'nl-BE'),  # DUTCH_BELGIAN
    (0x0413, 'nl-NL'),  # DUTCH DUTCH
    (0x0C09, 'en-AU'),  # ENGLISH_AUS
    (0x2809, 'en-BZ'),  # ENGLISH_BELIZE
    (0x1009, 'en-CA'),  # ENGLISH_CAN
    (0x2409, 'en-029'),  # ENGLISH_CARIBBEAN
    (0x4009, 'en-IN'),  # ENGLISH_INDIA
    (0x1809, 'en-IE'),  # ENGLISH_IRELAND
    (0x2009, 'en-JM'),  # ENGLISH_JAMAICA
    (0x4409, 'en-MY'),  # ENGLISH_MALAYSIA
    (0x1409, 'en-NZ'),  # ENGLISH_NZ
    (0x3409, 'en-PH'),  # ENGLISH_PHILIPPINES
    (0x4809, 'en-SG'),  # ENGLISH_SINGAPORE
    (0x1c09, 'en-ZA'),  # ENGLISH_SOUTH_AFRICA
    (0x2C09, 'en-TT'),  # ENGLISH_TRINIDAD
    (0x0809, 'en-GB'),  # ENGLISH_UK
    (0x0409, 'en-US'),  # ENGLISH_US
    (0x3009, 'en-ZW'),  # ENGLISH_ZIMBABWE
    (0x0425, 'et-EE'),  # ESTONIAN_ESTONIA
    (0x0438, 'fo-FO'),  # FAEROESE_FAROE_ISLANDS
    (0x0464, 'fil-PH'),  # FILIPINO_PHILIPPINES
    (0x040B, 'fi-FI'),  # FINNISH_FINLAND
    (0x080c, 'fr-BE'),  # FRENCH_BELGIAN
    (0x0C0C, 'fr-CA'),  # FRENCH_CANADIAN
    (0x040c, 'fr-FR'),  # FRENCH_FRENCH
    (0x140C, 'fr-LU'),  # FRENCH_LUXEMBOURG
    (0x180C, 'fr-MC'),  # FRENCH_MONACO
    (0x100C, 'fr-CH'),  # FRENCH_SWISS
    (0x0462, 'fy-NL'),  # FRISIAN_NETHERLANDS
    (0x0456, 'gl-ES'),  # GALICIAN_GALICIAN
    (0x0437, 'ka-GE'),  # GEORGIAN_GEORGIA
    (0x0C07, 'de-AT'),  # GERMAN_AUSTRIAN
    (0x0407, 'de-DE'),  # GERMAN_GERMAN
    (0x1407, 'de-LI'),  # GERMAN_LIECHTENSTEIN
    (0x1007, 'de-LU'),  # GERMAN_LUXEMBOURG
    (0x0807, 'de-CH'),  # GERMAN_SWISS
    (0x0408, 'el-GR'),  # GREEK_GREECE
    (0x046F, 'kl-GL'),  # GREENLANDIC_GREENLAND
    (0x0447, 'gu-IN'),  # GUJARATI_INDIA
    (0x0468, 'ha-NG'),  # HAUSA_NIGERIA_LATIN
    (0x0475, 'haw-US'),  # HAWAIIAN_US
    (0x040D, 'he-IL'),  # HEBREW_ISRAEL
    (0x0439, 'hi-IN'),  # HINDI_INDIA
    (0x040E, 'hu-HU'),  # HUNGARIAN_HUNGARY
    (0x040F, 'is-IS'),  # ICELANDIC_ICELAND
    (0x0470, 'ig-NG'),  # IGBO_NIGERIA
    (0x0421, 'id-ID'),  # INDONESIAN_INDONESIA
    (0x085D, 'iu-CA-Latin'),  # INUKTITUT_CANADA_LATIN
    (0x045D, 'iu-CA'),  # INUKTITUT_CANADA
    (0x083C, 'ga-IE'),  # IRISH_IRELAND
    (0x0434, 'xh-ZA'),  # XHOSA_SOUTH_AFRICA
    (0x0435, 'zu-ZA'),  # ZULU_SOUTH_AFRICA
    (0x0410, 'it-IT'),  # ITALIAN_ITALIAN
    (0x0810, 'it-CH'),  # ITALIAN_SWISS
    (0x0411, 'ja-JP'),  # JAPANESE_JAPAN
    (0x044B, 'kn-IN'),  # KANNADA_INDIA
    (0x043F, 'kk-KZ'),  # KAZAK_KAZAKHSTAN
    (0x0453, 'kh-KH'),  # KHMER_CAMBODIA
    (0x0486, 'qut-GT'),  # KICHE_GUATEMALA
    (0x0487, 'rw-RW'),  # KINYARWANDA_RWANDA
    (0x0457, 'kok-IN'),  # KONKANI_INDIA
    (0x0412, 'ko-KR'),  # KOREA_KOREAN
    (0x0440, 'ky-KG'),  # KYRGYZ_KYRGYZSTAN
    (0x0454, 'lo-LA'),  # LAO_LAO
    (0x0426, 'lv-LV'),  # LATVIAN_LATVIA
    (0x0427, 'lt-LT'),  # LITHUANIAN_LITHUANIA
    (0x082E, 'dsb-DE'),  # LOWER_SORBIAN_GERMANY
    (0x046E, 'lb-LU'),  # LUXEMBOURGISH_LUXEMBOURG
    (0x042F, 'mk-MK'),  # MACEDONIAN_MACEDONIA
    (0x083E, 'ms-BN'),  # MALAY_BRUNEI_DARUSSALAM
    (0x043e, 'ms-MY'),  # MALAY_MALAYSIA
    (0x044C, 'ml-IN'),  # MALAYALAM_INDIA
    (0x043A, 'mt-MT'),  # MALTESE_MALTA
    (0x0481, 'mi-NZ'),  # MAORI_NEW_ZEALAND
    (0x047A, 'arn-CL'),  # MAPUDUNGUN_CHILE'
    (0x044E, 'mr-IN'),  # MARATHI_INDIA
    (0x047C, 'moh-CA'),  # MOHAWK_MOHAWK
    (0x0450, 'mn-MN-Cyrllic'),  # MONGOLIAN_CYRILLIC_MONGOLIA
    (0x0850, 'mn-MN-Prc'),  # MONGOLIAN_PRC
    (0x0461, 'ne-NP'),  # NEPALI_NEPAL
    (0x0414, 'nb-NO'),  # NORWEGIAN_BOKMAL
    (0x0814, 'no-NO'),  # NORWEGIAN_NYNORSK
    (0x0482, 'oc-FR'),  # OCCITAN_FRANCE
    (0x0448, 'or-IN'),  # ORIYA_INDIA
    (0x0463, 'ps-AF'),  # PASHTO_AFGHANISTAN
    (0x0429, 'fa-IR'),  # PERSIAN_IRAN
    (0x0415, 'pl-PL'),  # POLISH_POLAND
    (0x0416, 'pt-BR'),  # PORTUGUESE_BRAZILIAN
    (0x0816, 'pt-PT'),  # PORTUGUESE-PORTUGUESE
    (0x0867, 'ff-SN'),  # PULAR_SENEGAL
    (0x0446, 'pa-IN'),  # PUNJABI_INDIA
    (0x0846, 'pa-PK'),  # PUNJABI_PAKISTAN
    (0x046B, 'quz-BO'),  # QUECHUA_BOLIVIA
    (0x086B, 'quz-EC'),  # QUECHUA_ECUADOR
    (0x0C6B, 'quz-PE'),  # QUECHUA_PERU
    (0x0418, 'ro-RO'),  # ROMANIAN_ROMANIA
    (0x0417, 'rm-CH'),  # ROMANSH_SWITZERLAND
    (0x0419, 'ru-RU'),  # RUSSIAN_RUSSIA
    (0x0485, 'sah-RU'),  # SAKHA_RUSSIA
    (0x243B, 'smn-FIl'),  # SAMI_INARI_FINLAND
    (0x103B, 'smj-NO'),  # SAMI_LULE_NORWAY
    (0x143B, 'smj-SE'),  # SAMI_LULE_SWEDEN
    (0x0C3B, 'se-FI'),  # SAMI_NORTHERN_FINLAND
    (0x043B, 'se-NO'),  # SAMI_NORTHERN_NORWAY
    (0x083B, 'se-SE'),  # SAMI_NORTHERN_SWEDEN
    (0x203B, 'sms-FI'),  # SAMI_SKOLT_FINLAND
    (0x183B, 'sma-NO'),  # SAMI_SOUTHERN_NORWAY
    (0x1C3B, 'sma-SE'),  # SAMI_SOUTHERN_SWEDEN
    (0x044F, 'sa-IN'),  # SANSKRIT_INDIA
    (0x7C1A, 'sr-Neutral'),  # SERBIAN_NEUTRAL
    (0x1C1A, 'sr-BA'),  # SERBIAN_BOSNIA_HERZEGOVINA_CYRILLIC
    (0x181A, 'sr-code-Latin'),  # SERBIAN_BOSNIA_HERZEGOVINA_LATIN
    (0x0C1A, 'sr-CS-Cyrillic'),  # SERBIAN_CYRILLIC
    (0x081A, 'sr-CS-Latin'),  # SERBIAN_LATIN
    (0x046C, 'nso-ZA'),  # SOTHO_NORTHERN_SOUTH_AFRICA
    (0x0832, 'tn-BW'),  # TSWANA_BOTSWANA
    (0x0432, 'tn-ZA'),  # TSWANA_SOUTH_AFRICA
    (0x0859, 'sd-PK'),  # SINDHI_PAKISTAN
    (0x045B, 'si-LK'),  # SINHALESE_SRI_LANKA
    (0x041B, 'sk-SK'),  # SLOVAK_SLOVAKIA
    (0x0424, 'sl-SI'),  # SLOVENIAN_SLOVENIA
    (0x2C0A, 'es-AR'),  # SPANISH_ARGENTINA
    (0x400A, 'es-BO'),  # SPANISH_BOLIVIA
    (0x340A, 'es-CL'),  # SPANISH_CHILE
    (0x240A, 'es-CO'),  # SPANISH_COLOMBIA
    (0x140A, 'es-CR'),  # SPANISH_COSTA_RICA
    (0x1C0A, 'es-DO'),  # SPANISH_DOMINICAN_REPUBLIC
    (0x300A, 'es-EC'),  # SPANISH_ECUADOR
    (0x440A, 'es-SV'),  # SPANISH_EL_SALVADOR
    (0x100A, 'es-GT'),  # SPANISH_GUATEMALA
    (0x480A, 'es-HN'),  # SPANISH_HONDURAS
    (0x080A, 'es-MX'),  # SPANISH_MEXICAN
    (0x4C0A, 'es-NI'),  # SPANISH_NICARAGUA
    (0x180A, 'es-PA'),  # SPANISH_PANAMA
    (0x3C0A, 'es-PY'),  # SPANISH_PARAGUAY
    (0x280A, 'es-PE'),  # SPANISH_PERU
    (0x500A, 'es-PR'),  # SPANISH_PUERTO_RICO
    (0x0C0A, 'es-ES-modern'),  # SPANISH_MODERN
    (0x040A, 'es-ES-traditional'),  # SPANISH
    (0x540A, 'es-US'),  # SPANISH_US
    (0x380A, 'es-UY'),  # SPANISH_URUGUAY
    (0x200A, 'es-VE'),  # SPANISH_VENEZUELA
    (0x0441, 'sw-KE'),  # SWAHILI
    (0x081D, 'sv-FI'),  # SWEDISH_FINLAND
    (0x041D, 'sv-SE'),  # SWEDISH_SWEDEN
    (0x045A, 'syr-SY'),  # SYRIAC
    (0x0428, 'tg-TJ'),  # TAJIK_TAJIKISTAN
    (0x085F, 'tzm-DZ'),  # TAMAZIGHT_ALGERIA_LATIN
    (0x0449, 'ta-IN'),  # TAMIL_INDIA
    (0x0849, 'ta-LK'),  # TAMIL_SRI_LANKA
    (0x0444, 'tt-RU'),  # TATAR_RUSSIA
    (0x044A, 'te-IN'),  # TELUGU_INDIA
    (0x041E, 'th-TH'),  # THAI_THAILAND
    (0x0451, 'bo-CN'),  # TIBETAN_PRC
    (0x0873, 'ti-ER'),  # TIGRINYA_ERITREA
    (0x0473, 'ti-ET'),  # TIGRINYA_ETHIOPIA
    (0x041F, 'tr-TR'),  # TURKISH_TURKEY
    (0x0442, 'tk-TM'),  # TURKMEN_TURKMENISTAN
    (0x0422, 'uk-UA'),  # UKRAINIAN_UKRAINE
    (0x042E, 'hsb-DE'),  # UPPER_SORBIAN_GERMANY
    (0x0820, 'ur-IN'),  # URDU_INDIA
    (0x0420, 'ur-PK'),  # URDU_PAKISTAN
    (0x0480, 'ug-CN'),  # UIGHUR_PRC
    (0x0843, 'uz-UZ-Cyrillic'),  # UZBEK_CYRILLIC
    (0x0443, 'uz-UZ-Latin'),  # UZBEK_LATIN
    (0x0803, 'ca-ES-Valencia'),  # VALENCIAN_VALENCIA
    (0x042A, 'vi-VN'),  # VIETNAMESE_VIETNAM
    (0x0452, 'cy-GB'),  # WELSH_UNITED_KINGDOM
    (0x0488, 'wo-SN'),  # WOLOF_SENEGAL
    (0x0478, 'ii-CN'),  # YI_PRC
    (0x046A, 'yo-NG'),  # YORUBA_NIGERIA
)

def getLangCodes():
    return langcodes
