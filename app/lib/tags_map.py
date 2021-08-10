classes = {
    "cv-dl" : 1,
    "cv-dr" : 2,
    "cv-f" : 3,
    "cv-sl" : 4,
    "cv-sr" : 5,
    "ear-dl-l" : 6,
    "ear-dl-r" : 7,
    "ear-dr-l" : 8,
    "ear-dr-r" : 9,
    "ear-fl" : 10,
    "ear-fr" : 11,
    "ear-sl" : 12,
    "ear-sr" : 13,
    "eye-dl-l" : 14,
    "eye-dl-r" : 15,
    "eye-dr-l" : 16,
    "eye-dr-r" : 17,
    "eye-fl" : 18,
    "eye-fr" : 19,
    "eye-sl" : 20,
    "eye-sr" : 21,
    "nose-dl" : 22,
    "nose-dr" : 23,
    "nose-f" : 24,
    "nose-sl" : 25,
    "nose-sr" : 26,
    "whisker-dl" : 27,
    "whisker-dr" : 28,
    "whisker-f" : 29,
    "whisker-sl" : 30,
    "whisker-sr" : 31,
    "cv-f-marking" : 32,
    "cv-r-marking" : 33,
    "cv-l-marking" : 34,
    "eye-r-marking" : 35,
    "eye-l-marking" : 36,
    "ear-r-marking" : 37,
    "ear-l-marking" : 38,
    "nose-marking" : 39,
    "whisker-l-marking" : 40,
    "whisker-r-marking" : 41,
    "main-id-marking" : 42,
    "body-marking" : 43,
    "full-body" : 44,
    }

tag_key = {
    (1,2,3,4,5):'cv',               # CV Image
    (40,):'whisker-left',                            # Whisker Right
    (41,):'whisker-right',                           # Whisker Left
    (27,28,29,30,31):'whisker',                # Whisker (Not used in algorithm)
    (6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26, 32,33,34,35,36,37,38,39,40,41,42,43):'marking', # Marking
    (42,):'main-id',                                  # Main Id
    (44,):'full-body'                                # Full Body
    }


