

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
# https://winprotocoldoc.blob.core.windows.net/productionwindowsarchives/MS-LCID/%5bMS-LCID%5d.pdf
# https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/63d3d639-7fd2-4afb-abbe-0d5b5551eef8
# https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
langcodes = (
    (0x0C00, 'custom default'),  # Default custom locale language-Default custom sublanguage'
    (0x1400, 'ui_custom_default'),  # Default custom MUI locale language-Default custom MUI sublanguage
    (0x007f, 'invariant'),  # Invariant locale language-invariant sublanguage
    (0x0000, 'neutral'),  # Neutral locale language-Neutral sublanguage
    (0x0800, 'sys default'),  # System default locale language-System default sublanguage
    (0x1000, 'custom unspecified'),  # Unspecified custom locale language-Unspecified custom sublanguage
    (0x0400, 'default'),  # User default locale language-User default sublanguage
    (0x0036, 'af'),  # AFRIKAANS
    (0x0436, 'af-ZA'),  # AFRIKAANS_SOUTH_AFRICA
    (0x001C, 'sq'),  # ALBANIAN
    (0x041C, 'sq-AL'),  # ALBANIAN_ALBANIA
    (0x0084, 'gsw'),  # ALSATIAN
    (0x0484, 'gsw-FR'),  # ALSATIAN_FRANCE
    (0x005E, 'am'),  # AMHARIC
    (0x045E, 'am-ET'),  # AMHARIC_ETHIOPIA
    (0x0001, 'ar'),  # ARABIC
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
    (0x4401, 'ar-Ploc-SA'),  # ARABIC PSEUDO LOCALE
    (0x4801, 'ar-145'),
    (0x002B, 'hy'),  # ARMENIAN
    (0x042B, 'hy-AM'),  # ARMENIAN_ARMENIA
    (0x004D, 'as'),  # ASSAMESE
    (0x044D, 'as-IN'),  # ASSAMESE_INDIA
    (0x002C, 'az'),  # AZERBAIJANI (LATIN)
    (0x742C, 'az-Cyrl'),  # AZERBAIJANI (CYRILLIC)
    (0x082C, 'az-Cyrl-AZ'),  # AZERBAIJANI (CYRILLIC) AZERBAIJAN
    (0x782C, 'az-Latn'),  # AZERBAIJANI (LATIN)
    (0x042C, 'az-Latn-AZ'),  # AZERBAIJANI (LATIN) AZERBAIJAN
    (0x0045, 'bn'),  # BANGLA
    (0x0845, 'bn-BD'),  # BANGLA BANGLADESH
    (0x0445, 'bn-IN'),  # BANGLA INDIA
    (0x006D, 'ba'),  # BASHKIR
    (0x046D, 'ba-RU'),  # BASHKIR_RUSSIA
    (0x002D, 'eu'),  # BASQUE
    (0x042D, 'eu-ES'),  # BASQUE SPAIN
    (0x0023, 'be'),  # BELARUSIAN
    (0x0423, 'be-BY'),  # BELARUSIAN_BELARUS
    (0x0066, 'bin'),  # BINI
    (0x0466, 'bin-NG'),  # BINI NIGERIA
    (0x641A, 'bs-Cyrl'),  # BOSNIAN (CYRILLIC)
    (0x201A, 'bs-Cyrl-BA'),  # BOSNIAN (CYRILLIC) BOSNIA AND HERZEGOVINA
    (0x781A, 'bs'),  # BOSNIAN (LATIN)
    (0x681A, 'bs-Latn'),  # BOSNIAN (LATIN)
    (0x141A, 'bs-Latn-BA'),  # BOSNIAN (LATIN) BOSNIA AND HERZEGOVINA
    (0x007E, 'br'),  # BRETON
    (0x047E, 'br-FR'),  # BRETON_FRANCE
    (0x0002, 'bg'),  # BULGARIAN
    (0x0402, 'bg-BG'),  # BULGARIAN_BULGARIA
    (0x0055, 'my'),  # BURMESE
    (0x0455, 'my-MM'),  # BURMESE MYANMAR
    (0x0003, 'ca'),  # CATALAN
    (0x0403, 'ca-ES'),  # CATALAN_CATALAN
    (0x0092, 'ku'),  # CENTRAL KURDISH
    (0x7C92, 'ku-Arab'),  # CENTRAL KURDISH
    (0x0492, 'ku-Arab-IQ'),  # CENTRAL KURDISH IRAQ
    (0x005C, 'chr'),  # CHEROKEE
    (0x045C, 'chr-Cher-US'),  # CHEROKEE UNITED STATES
    (0x7C5C, 'chr-Cher'),  # CHEROKEE
    (0x7804, 'zh'),  # CHINESE (SIMPLIFIED)
    (0x0C04, 'zh-HK'),  # CHINESE_HONGKONG
    (0x1404, 'zh-MO'),  # CHINESE_MACAU
    (0x1004, 'zh-SG'),  # CHINESE_SINGAPORE
    (0x0804, 'zh-CN'),  # CHINESE (SIMPLIFIED) PEOPLE'S REPUBLIC OF CHINA
    (0x0404, 'zh-TW'),  # CHINESE (TRADITIONAL) TAIWAN
    (0x0004, 'zh-Hans'),  # CHINESE_SIMPLIFIED
    (0x7C04, 'zh-Hant'),  # CHINESE_TRADITIONAL
    (0x0083, 'co'),  # CORSICAN
    (0x0483, 'co-FR'),  # CORSICAN_FRANCE
    (0x001A, 'hr'),  # CROATIAN Neutral
    (0x101A, 'hr-BA'),  # CROATIAN_BOSNIA_HERZEGOVINA_LATIN
    (0x041A, 'hr-HR'),  # CROATIAN_CROATIA
    (0x0005, 'cs'),  # CZECH
    (0x0405, 'cs-CZ'),  # CZECH_CZECH_REPUBLIC
    (0x0006, 'da'),  # DANISH
    (0x0406, 'da-DK'),  # DANISH_DENMARK
    (0x008C, 'prs'),  # DARI
    (0x048C, 'prs-AF'),  # DARI_AFGHANISTAN
    (0x0065, 'dv'),  # DIVEHI
    (0x0465, 'dv-MV'),  # DIVEHI_MALDIVES
    (0x0013, 'nl'),  # DUTCH
    (0x0813, 'nl-BE'),  # DUTCH_BELGIAN
    (0x0413, 'nl-NL'),  # DUTCH DUTCH
    (0x0C51, 'dz-BT'),  # DZONGKHA BHUTAN
    (0x0009, 'en'),  # ENGLISH
    (0x0C09, 'en-AU'),  # ENGLISH_AUS
    (0x2809, 'en-BZ'),  # ENGLISH_BELIZE
    (0x1009, 'en-CA'),  # ENGLISH_CAN
    (0x2409, 'en-029'),  # ENGLISH_CARIBBEAN
    (0x3C09, 'en-HK'),  # ENGLISH HONG KONG
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
    (0x4C09, 'en-AE'),  # ENGLISH UNITED ARAB EMIRATES
    (0x3009, 'en-ZW'),  # ENGLISH_ZIMBABWE
    (0x3809, 'en-ID'),  # ENGLISH INDONESIAN
    (0x5009, 'en-BH'),  # ENGLISH BAHRAIN
    (0x5409, 'en-EG'),  # ENGLISH EGYPT
    (0x5809, 'en-JO'),  # ENGLISH JORDAN
    (0x5C09, 'en-KW'),  # ENGLISH KUWAIT
    (0x6009, 'en-TR'),  # ENGLISH TURKEY
    (0x6409, 'en-YE'),  # ENGLISH YEMEN
    (0x0025, 'et'),  # ESTONIAN
    (0x0425, 'et-EE'),  # ESTONIAN_ESTONIA
    (0x0038, 'fo'),  # FAROESE
    (0x0438, 'fo-FO'),  # FAEROESE_FAROE_ISLANDS
    (0x0064, 'fil'),  # FILIPINO
    (0x0464, 'fil-PH'),  # FILIPINO_PHILIPPINES
    (0x000B, 'fi'),  # FINNISH
    (0x040B, 'fi-FI'),  # FINNISH_FINLAND
    (0x000C, 'fr'),  # FRENCH
    (0x080c, 'fr-BE'),  # FRENCH_BELGIAN
    (0x0C0C, 'fr-CA'),  # FRENCH_CANADIAN
    (0x2C0C, 'fr-CM'),  # FRENCH CAMEROON
    (0x1C0C, 'fr-029'),  # FRENCH CARIBBEAN
    (0x240C, 'fr-CD'),  # FRENCH CONGO, DRC
    (0x300C, 'fr-CI'),  # FRENCH CÔTE D'IVOIRE
    (0x040c, 'fr-FR'),  # FRENCH_FRENCH
    (0x3C0C, 'fr-HT'),  # FRENCH HAITI
    (0x140C, 'fr-LU'),  # FRENCH_LUXEMBOURG
    (0x340C, 'fr-ML'),  # FRENCH MALI
    (0x180C, 'fr-MC'),  # FRENCH_MONACO
    (0x380C, 'fr-MA'),  # FRENCH MOROCCO
    (0x200C, 'fr-RE'),  # FRENCH REUNION
    (0x280C, 'fr-SN'),  # FRENCH SENEGAL
    (0x100C, 'fr-CH'),  # FRENCH_SWISS
    (0xE40C, 'fr-015'),
    (0x0062, 'fy'),  # FRISIAN
    (0x0462, 'fy-NL'),  # FRISIAN_NETHERLANDS
    (0x0067, 'ff'),  # FULAH
    (0x7C67, 'ff-Latn'),  # FULAH (LATIN)
    (0x0467, 'ff-NG'),  # FULAH NIGERIA
    (0x0867, 'ff-Latn-SN'),  # FULAH SENEGAL
    (0x0056, 'gl'),  # GALICIAN
    (0x0456, 'gl-ES'),  # GALICIAN_GALICIAN
    (0x0037, 'ka'),  # GEORGIAN
    (0x0437, 'ka-GE'),  # GEORGIAN_GEORGIA
    (0x0007, 'de'),  # GERMAN
    (0x0C07, 'de-AT'),  # GERMAN_AUSTRIAN
    (0x0407, 'de-DE'),  # GERMAN_GERMAN
    (0x1407, 'de-LI'),  # GERMAN_LIECHTENSTEIN
    (0x1007, 'de-LU'),  # GERMAN_LUXEMBOURG
    (0x0807, 'de-CH'),  # GERMAN_SWISS
    (0x0008, 'el'),  # GREEK
    (0x0408, 'el-GR'),  # GREEK_GREECE
    (0x006F, 'kl'),  # GREENLANDIC
    (0x046F, 'kl-GL'),  # GREENLANDIC_GREENLAND
    (0x0074, 'gn'),  # GUARANI
    (0x0474, 'gn-PY'),  # GUARANI PARAGUAY
    (0x0047, 'gu'),  # GUJARATI
    (0x0447, 'gu-IN'),  # GUJARATI_INDIA
    (0x0068, 'ha'),  # HAUSA (LATIN)
    (0x7C68, 'ha-Latn'),  # HAUSA (LATIN)
    (0x0468, 'ha-Latn-NG'),  # HAUSA (LATIN) NIGERIA
    (0x0075, 'haw'),  # HAWAIIAN
    (0x0475, 'haw-US'),  # HAWAIIAN_US
    (0x000D, 'he'),  # HEBREW
    (0x040D, 'he-IL'),  # HEBREW_ISRAEL
    (0x0039, 'hi'),  # HINDI
    (0x0439, 'hi-IN'),  # HINDI_INDIA
    (0x000E, 'hu'),  # HUNGARIAN
    (0x040E, 'hu-HU'),  # HUNGARIAN_HUNGARY
    (0x000F, 'is'),  # ICELANDIC
    (0x040F, 'is-IS'),  # ICELANDIC_ICELAND
    (0x0070, 'ig'),  # IGBO
    (0x0470, 'ig-NG'),  # IGBO_NIGERIA
    (0x0021, 'id'),  # INDONESIAN
    (0x0421, 'id-ID'),  # INDONESIAN_INDONESIA
    (0x0069, 'ibb'),  # IBIBIO
    (0x0469, 'ibb-NG'),  # IBIBIO NIGERIA
    (0x005D, 'iu'),  # INUKTITUT (LATIN)
    (0x7C5D, 'iu-Latn'),  # INUKTITUT (LATIN)
    (0x085D, 'iu-Latn-CA'),  # INUKTITUT (LATIN) CANADA
    (0x785D, 'iu-Cans'),  # INUKTITUT (SYLLABICS)
    (0x045D, 'iu-Cans-CA'),  # INUKTITUT (SYLLABICS) CANADA
    (0x003C, 'ga'),  # IRISH
    (0x083C, 'ga-IE'),  # IRISH_IRELAND
    (0x0010, 'it'),  # ITALIAN
    (0x0410, 'it-IT'),  # ITALIAN_ITALIAN
    (0x0810, 'it-CH'),  # ITALIAN_SWISS
    (0x0011, 'ja'),  # JAPANESE
    (0x0411, 'ja-JP'),  # JAPANESE_JAPAN
    (0x0811, 'ja-Ploc-JP'),  # JAPANESE PSEUDO LOCALE
    (0x0071, 'kr'),  # KANURI
    (0x0471, 'kr-Latn-NG'),  # KANURI (LATIN) NIGERIA
    (0x004B, 'kn'),  # KANNADA
    (0x044B, 'kn-IN'),  # KANNADA_INDIA
    (0x0060, 'ks'),  # KASHMIRI
    (0x0460, 'ks-Arab'),  # KASHMIRI PERSO-ARABIC
    (0x0860, 'ks-Deva-IN'),  # KASHMIRI (DEVANAGARI) INDIA
    (0x003F, 'kk'),  # KAZAKH
    (0x043F, 'kk-KZ'),  # KAZAK_KAZAKHSTAN
    (0x083F, 'kk-Latn-KZ'),  # KAZAK (LATIN) KAZAKHSTAN
    (0x7C3F, 'kk-Latn'),  # KAZAK (LATIN)
    (0x783F, 'kk-Cyrl'),  # KAZAK (CYRILLIC)
    (0x0053, 'km'),  # KHMER
    (0x0453, 'km-KH'),  # KHMER CAMBODIA
    (0x0086, 'quc'),  # K'ICHE
    (0x0486, 'quc-Latn-GT'),  # K'ICHE GUATEMALA
    (0x0087, 'rw'),  # KINYARWANDA
    (0x0487, 'rw-RW'),  # KINYARWANDA_RWANDA
    (0x0057, 'kok'),  # KONKANI
    (0x0457, 'kok-IN'),  # KONKANI_INDIA
    (0x0012, 'ko'),  # KOREAN
    (0x0412, 'ko-KR'),  # KOREA_KOREAN
    (0x0040, 'ky'),  # KYRGYZ
    (0x0440, 'ky-KG'),  # KYRGYZ_KYRGYZSTAN
    (0x0054, 'lo'),  # LAO
    (0x0454, 'lo-LA'),  # LAO_LAO
    (0x0076, 'la'),  # LATIN
    (0x0476, 'la-VA'),  # LATIN VATICAN CITY
    (0x0026, 'lv'),  # LATVIAN
    (0x0426, 'lv-LV'),  # LATVIAN_LATVIA
    (0x0027, 'lt'),  # LITHUANIAN
    (0x0427, 'lt-LT'),  # LITHUANIAN_LITHUANIA
    (0x7C2E, 'dsb'),  # LOWER SORBIAN
    (0x082E, 'dsb-DE'),  # LOWER_SORBIAN_GERMANY
    (0x006E, 'lb'),  # LUXEMBOURGISH
    (0x046E, 'lb-LU'),  # LUXEMBOURGISH_LUXEMBOURG
    (0x002F, 'mk'),  # MACEDONIAN
    (0x042F, 'mk-MK'),  # MACEDONIAN_MACEDONIA
    (0x003E, 'ms'),  # MALAY
    (0x083E, 'ms-BN'),  # MALAY_BRUNEI_DARUSSALAM
    (0x043e, 'ms-MY'),  # MALAY_MALAYSIA
    (0x004C, 'ml'),  # MALAYALAM
    (0x044C, 'ml-IN'),  # MALAYALAM_INDIA
    (0x003A, 'mt'),  # MALTESE
    (0x043A, 'mt-MT'),  # MALTESE_MALTA
    (0x0058, 'mni'),  # MANIPURI
    (0x0458, 'mni-IN'),  # MANIPURI INDIA
    (0x0081, 'mi'),  # MAORI
    (0x0481, 'mi-NZ'),  # MAORI_NEW_ZEALAND
    (0x007A, 'arn'),  # MAPUDUNGUN
    (0x047A, 'arn-CL'),  # MAPUDUNGUN_CHILE
    (0x004E, 'mr'),  # MARATHI
    (0x044E, 'mr-IN'),  # MARATHI_INDIA
    (0x007C, 'moh'),  # MOHAWK
    (0x047C, 'moh-CA'),  # MOHAWK_MOHAWK
    (0x0050, 'mn'),  # MONGOLIAN (CYRILLIC)
    (0x7850, 'mn-Cyrl'),  # MONGOLIAN (CYRILLIC)
    (0x7C50, 'mn-Mong'),  # MONGOLIAN (TRADITIONAL MONGOLIAN)
    (0x0C50, 'mn-Mong-MN'),  # MONGOLIAN (TRADITIONAL MONGOLIAN) MONGOLIA
    (0x0450, 'mn-MN'),  # MONGOLIAN (CYRILLIC) MONGOLIA
    (0x0850, 'mn-Mong-CN'),  # MONGOLIAN (TRADITIONAL MONGOLIAN) PEOPLE'S REPUBLIC OF CHINA
    (0x0061, 'ne'),  # NEPALI
    (0x0861, 'ne-IN'),  # NEPALI INDIA
    (0x0461, 'ne-NP'),  # NEPALI_NEPAL
    (0x0014, 'no'),  # NORWEGIAN (BOKMAL)
    (0x7C14, 'nb'),  # NORWEGIAN (BOKMAL)
    (0x7814, 'nn'),  # NORWEGIAN (NYNORSK)
    (0x0814, 'nn-NO'),  # NORWEGIAN (NYNORSK) NORWAY
    (0x0414, 'nb-NO'),  # NORWEGIAN_BOKMAL
    (0x0082, 'oc'),  # OCCITAN
    (0x0482, 'oc-FR'),  # OCCITAN_FRANCE
    (0x0048, 'or'),  # ODIA
    (0x0448, 'or-IN'),  # ORIYA_INDIA
    (0x0472, 'om-ET'),  # OROMO ETHIOPIA
    (0x0072, 'om'),  # OROMO
    (0x0079, 'pap'),  # PAPIAMENTO
    (0x0479, 'pap-029'),
    (0x0063, 'ps'),  # PASHTO
    (0x0463, 'ps-AF'),  # PASHTO_AFGHANISTAN
    (0x0029, 'fa'),  # PERSIAN
    (0x0429, 'fa-IR'),  # PERSIAN_IRAN
    (0x0015, 'pl'),  # POLISH
    (0x0415, 'pl-PL'),  # POLISH_POLAND
    (0x0016, 'pt'),  # PORTUGUESE
    (0x0416, 'pt-BR'),  # PORTUGUESE_BRAZILIAN
    (0x0816, 'pt-PT'),  # PORTUGUESE-PORTUGUESE
    (0x05FE, 'qps-ploca'),  # PSEUDO LANGUAGE PSEUDO LOCALE FOR EAST ASIAN/COMPLEX SCRIPT LOCALIZATION TESTING
    (0x0501, 'qps-ploc'),  # PSEUDO LANGUAGE PSEUDO LOCALE USED FOR LOCALIZATION TESTING
    (0x09FF, 'qps-plocm'),  # PSEUDO LANGUAGE PSEUDO LOCALE USED FOR LOCALIZATION TESTING OF MIRRORED LOCALES
    (0x0046, 'pa'),  # PUNJABI
    (0x7C46, 'pa-Arab'),  # PUNJABI
    (0x0446, 'pa-IN'),  # PUNJABI_INDIA
    (0x0846, 'pa-Arab-PK'),  # PUNJABI ISLAMIC REPUBLIC OF PAKISTAN
    (0x006B, 'quz'),  # QUECHUA
    (0x046B, 'quz-BO'),  # QUECHUA_BOLIVIA
    (0x086B, 'quz-EC'),  # QUECHUA_ECUADOR
    (0x0C6B, 'quz-PE'),  # QUECHUA_PERU
    (0x0018, 'ro'),  # ROMANIAN
    (0x0418, 'ro-RO'),  # ROMANIAN_ROMANIA
    (0x0818, 'ro-MD'),  # ROMANIAN MOLDOVA
    (0x0017, 'rm'),  # ROMANSH
    (0x0417, 'rm-CH'),  # ROMANSH_SWITZERLAND
    (0x0019, 'ru'),  # RUSSIAN
    (0x0419, 'ru-RU'),  # RUSSIAN_RUSSIA
    (0x0819, 'ru-MD'),  # RUSSIAN MOLDOVA
    (0x0085, 'sah'),  # SAKHA
    (0x0485, 'sah-RU'),  # SAKHA_RUSSIA
    (0x703B, 'smn'),  # SAMI (INARI)
    (0x243B, 'smn-FI'),  # SAMI (INARI) FINLAND
    (0x7C3B, 'smj'),  # SAMI (LULE)
    (0x103B, 'smj-NO'),  # SAMI_LULE_NORWAY
    (0x143B, 'smj-SE'),  # SAMI_LULE_SWEDEN
    (0x003B, 'se'),  # SAMI (NORTHERN)
    (0x0C3B, 'se-FI'),  # SAMI_NORTHERN_FINLAND
    (0x043B, 'se-NO'),  # SAMI_NORTHERN_NORWAY
    (0x083B, 'se-SE'),  # SAMI_NORTHERN_SWEDEN
    (0x743B, 'sms'),  # SAMI (SKOLT)
    (0x203B, 'sms-FI'),  # SAMI_SKOLT_FINLAND
    (0x783B, 'sma'),  # SAMI (SOUTHERN)
    (0x183B, 'sma-NO'),  # SAMI_SOUTHERN_NORWAY
    (0x1C3B, 'sma-SE'),  # SAMI_SOUTHERN_SWEDEN
    (0x004F, 'sa'),  # SANSKRIT
    (0x044F, 'sa-IN'),  # SANSKRIT_INDIA
    (0x0091, 'gd'),  # SCOTTISH GAELIC
    (0x0491, 'gd-GB'),  # SCOTTISH GAELIC UNITED KINGDOM
    (0x6C1A, 'sr-Cyrl'),  # SERBIAN (CYRILLIC)
    (0x1C1A, 'sr-Cyrl-BA'),  # SERBIAN (CYRILLIC) BOSNIA AND HERZEGOVINA
    (0x301A, 'sr-Cyrl-ME'),  # SERBIAN (CYRILLIC) MONTENEGRO
    (0x281A, 'sr-Cyrl-RS'),  # SERBIAN (CYRILLIC) SERBIA
    (0x0C1A, 'sr-Cyrl-CS'),  # SERBIAN (CYRILLIC) SERBIA AND MONTENEGRO (FORMER)
    (0x701A, 'sr-Latn'),  # SERBIAN (LATIN)
    (0x7C1A, 'sr'),  # SERBIAN (LATIN)
    (0x181A, 'sr-Latn-BA'),  # SERBIAN (LATIN) BOSNIA AND HERZEGOVINA
    (0x2C1A, 'sr-Latn-ME'),  # SERBIAN (LATIN) MONTENEGRO
    (0x241A, 'sr-Latn-RS'),  # SERBIAN (LATIN) SERBIA
    (0x081A, 'sr-Latn-CS'),  # SERBIAN (LATIN) SERBIA AND MONTENEGRO (FORMER)
    (0x0032, 'tn'),  # SETSWANA
    (0x0832, 'tn-BW'),  # TSWANA_BOTSWANA
    (0x0432, 'tn-ZA'),  # TSWANA_SOUTH_AFRICA
    (0x0059, 'sd'),  # SINDHI
    (0x7C59, 'sd-Arab'),  # SINDHI
    (0x0459, 'sd-Deva-IN'),  # SINDHI (DEVANAGARI) INDIA
    (0x0859, 'sd-Arab-PK'),  # SINDHI ISLAMIC REPUBLIC OF PAKISTAN
    (0x005B, 'si'),  # SINHALA
    (0x045B, 'si-LK'),  # SINHALESE_SRI_LANKA
    (0x001B, 'sk'),  # SLOVAK
    (0x041B, 'sk-SK'),  # SLOVAK_SLOVAKIA
    (0x0024, 'sl'),  # SLOVENIAN
    (0x0424, 'sl-SI'),  # SLOVENIAN_SLOVENIA
    (0x0077, 'so'),  # SOMALI
    (0x0477, 'so-SO'),  # SOMALI SOMALIA
    (0x0030, 'st'),  # SOTHO
    (0x0430, 'st-ZA'),  # SOTHO SOUTH AFRICA
    (0x006C, 'nso'),  # SESOTHO SA LEBOA
    (0x046C, 'nso-ZA'),  # SOTHO_NORTHERN_SOUTH_AFRICA
    (0x000A, 'es'),  # SPANISH
    (0x2C0A, 'es-AR'),  # SPANISH_ARGENTINA
    (0x400A, 'es-BO'),  # SPANISH_BOLIVIA
    (0x340A, 'es-CL'),  # SPANISH_CHILE
    (0x240A, 'es-CO'),  # SPANISH_COLOMBIA
    (0x140A, 'es-CR'),  # SPANISH_COSTA_RICA
    (0x5C0A, 'es-CU'),  # SPANISH CUBA
    (0x1C0A, 'es-DO'),  # SPANISH_DOMINICAN_REPUBLIC
    (0x300A, 'es-EC'),  # SPANISH_ECUADOR
    (0x440A, 'es-SV'),  # SPANISH_EL_SALVADOR
    (0x100A, 'es-GT'),  # SPANISH_GUATEMALA
    (0x480A, 'es-HN'),  # SPANISH_HONDURAS
    (0x580A, 'es-419'),  # SPANISH LATIN AMERICA
    (0x080A, 'es-MX'),  # SPANISH_MEXICAN
    (0x4C0A, 'es-NI'),  # SPANISH_NICARAGUA
    (0x180A, 'es-PA'),  # SPANISH_PANAMA
    (0x3C0A, 'es-PY'),  # SPANISH_PARAGUAY
    (0x280A, 'es-PE'),  # SPANISH_PERU
    (0x500A, 'es-PR'),  # SPANISH_PUERTO_RICO
    (0x040A, 'es-ES_tradnl'),  # SPANISH SPAIN
    (0x0C0A, 'es-ES'),  # SPANISH SPAIN
    (0x540A, 'es-US'),  # SPANISH_US
    (0x380A, 'es-UY'),  # SPANISH_URUGUAY
    (0x200A, 'es-VE'),  # SPANISH_VENEZUELA
    (0x0041, 'sw'),  # KISWAHILI
    (0x0441, 'sw-KE'),  # SWAHILI
    (0x001D, 'sv'),  # SWEDISH
    (0x081D, 'sv-FI'),  # SWEDISH_FINLAND
    (0x041D, 'sv-SE'),  # SWEDISH_SWEDEN
    (0x005A, 'syr'),  # SYRIAC
    (0x045A, 'syr-SY'),  # SYRIAC
    (0x0028, 'tg'),  # TAJIK (CYRILLIC)
    (0x7C28, 'tg-Cyrl'),  # TAJIK (CYRILLIC)
    (0x0428, 'tg-Cyrl-TJ'),  # TAJIK (CYRILLIC) TAJIKISTAN
    (0x005F, 'tzm'),  # TAMAZIGHT (LATIN)
    (0x0C5F, 'tzm-MA'),  # TAMAZIGHT MOROCCO
    (0x7C5F, 'tzm-Latn'),  # TAMAZIGHT (LATIN)
    (0x085F, 'tzm-Latn-DZ'),  # TAMAZIGHT (LATIN) ALGERIA
    (0x045F, 'tzm-Arab-MA'),  # CENTRAL ATLAS TAMAZIGHT (ARABIC) MOROCCO
    (0x785F, 'tzm-Tfng'),  # TAMAZIGHT (TIFINAGH)
    (0x105F, 'tzm-Tfng-MA'),  # TAMAZIGHT (TIFINAGH MOROCCO)
    (0x0049, 'ta'),  # TAMIL
    (0x0449, 'ta-IN'),  # TAMIL_INDIA
    (0x0849, 'ta-LK'),  # TAMIL_SRI_LANKA
    (0x0044, 'tt'),  # TATAR
    (0x0444, 'tt-RU'),  # TATAR_RUSSIA
    (0x004A, 'te'),  # TELUGU
    (0x044A, 'te-IN'),  # TELUGU_INDIA
    (0x001E, 'th'),  # THAI
    (0x041E, 'th-TH'),  # THAI_THAILAND
    (0x0051, 'bo'),  # TIBETAN
    (0x0451, 'bo-CN'),  # TIBETAN_PRC
    (0x0851, 'bo-BT'),  # TIBETAN BHUTAN
    (0x0073, 'ti'),  # TIGRINYA
    (0x0873, 'ti-ER'),  # TIGRINYA_ERITREA
    (0x0473, 'ti-ET'),  # TIGRINYA_ETHIOPIA
    (0x0031, 'ts'),  # TSONGA
    (0x0431, 'ts-ZA'),  # TSONGA SOUTH AFRICA
    (0x001F, 'tr'),  # TURKISH
    (0x041F, 'tr-TR'),  # TURKISH_TURKEY
    (0x0042, 'tk'),  # TURKMEN
    (0x0442, 'tk-TM'),  # TURKMEN_TURKMENISTAN
    (0x0080, 'ug'),  # UYGHUR
    (0x0480, 'ug-CN'),  # UIGHUR_PRC
    (0x0022, 'uk'),  # UKRAINIAN
    (0x0422, 'uk-UA'),  # UKRAINIAN_UKRAINE
    (0x002E, 'hsb'),  # UPPER SORBIAN
    (0x042E, 'hsb-DE'),  # UPPER_SORBIAN_GERMANY
    (0x0020, 'ur'),  # URDU
    (0x0820, 'ur-IN'),  # URDU_INDIA
    (0x0420, 'ur-PK'),  # URDU_PAKISTAN
    (0x0043, 'uz'),  # UZBEK (LATIN)
    (0x7C43, 'uz-Latn'),  # UZBEK (LATIN)
    (0x0443, 'uz-Latn-UZ'),  # UZBEK (LATIN) UZBEKISTAN
    (0x7843, 'uz-Cyrl'),  # UZBEK (CYRILLIC)
    (0x0843, 'uz-Cyrl-UZ'),  # UZBEK (CYRILLIC) UZBEKISTAN
    (0x0803, 'ca-ES-Valencia'),  # VALENCIAN_VALENCIA
    (0x0033, 've'),  # VENDA
    (0x0433, 've-ZA'),  # VENDA SOUTH AFRICA
    (0x002A, 'vi'),  # VIETNAMESE
    (0x042A, 'vi-VN'),  # VIETNAMESE_VIETNAM
    (0x0052, 'cy'),  # WELSH
    (0x0452, 'cy-GB'),  # WELSH_UNITED_KINGDOM
    (0x0088, 'wo'),  # WOLOF
    (0x0488, 'wo-SN'),  # WOLOF_SENEGAL
    (0x0034, 'xh'),  # XHOSA
    (0x0434, 'xh-ZA'),  # XHOSA_SOUTH_AFRICA
    (0x0078, 'ii'),  # YI
    (0x0478, 'ii-CN'),  # YI_PRC
    (0x003D, 'yi'),  # YIDDISH
    (0x043D, 'yi-001'),  # YIDDISH WORLD
    (0x006A, 'yo'),  # YORUBA
    (0x046A, 'yo-NG'),  # YORUBA_NIGERIA
    (0x0035, 'zu'),  # ZULU
    (0x0435, 'zu-ZA'),  # ZULU_SOUTH_AFRICA

    # See Section 2.2.1 of MS-LCID
    (0x2000, 'custom transient 0x2000'),
    (0x2400, 'custom transient 0x2400'),
    (0x2800, 'custom transient 0x2800'),
    (0x2C00, 'custom transient 0x2C00'),
    (0x3000, 'custom transient 0x3000'),
    (0x3400, 'custom transient 0x3400'),
    (0x3800, 'custom transient 0x3800'),
    (0x3C00, 'custom transient 0x3C00'),
    (0x4000, 'custom transient 0x4000'),
    (0x4400, 'custom transient 0x4400'),
    (0x4800, 'custom transient 0x4800'),
    (0x4C00, 'custom transient 0x4C00'),
    (0x007B, 'undefined and unreserved 0x007B'),
    (0x007D, 'undefined and unreserved 0x007D'),
    (0x0089, 'undefined and unreserved 0x0089'),
    (0x008A, 'undefined and unreserved 0x008A'),
    (0x008B, 'undefined and unreserved 0x008B'),
    (0x008D, 'undefined and unreserved 0x008D'),
    (0x008E, 'undefined and unreserved 0x008E'),
    (0x008F, 'undefined and unreserved 0x008F'),
    (0x0090, 'undefined and unreserved 0x0090'),
    (0x0827, 'undefined and unreserved 0x0827'),
    (0x2008, 'undefined and unreserved 0x2008'),
    (0xF2EE, 'reserved 0xF2EE'),
    (0xEEEE, 'reserved 0xEEEE'),

    (0x048D, 'plt-MG'),  # MALAGASY
    (0x048E, 'zh-yue-HK'),  # CHINESE (YUE) HONG KONG
    (0x048F, 'tdd-Tale-CN'),  # TAI NÜA (TAI LE) PEOPLE'S REPUBLIC OF CHINA
    (0x0490, 'khb-Talu-CN'),  # LÜ  (NEW TAI LUE) PEOPLE'S REPUBLIC OF CHINA

    (0x0093, 'quc, reserved'),
    (0x0493, 'quc-CO, reserved'),
)

def getLangCodes():
    return langcodes
