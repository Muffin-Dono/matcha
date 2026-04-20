# Tournament settings
INFO = {
    "full_name": "Summer Skirmish 2025",
    "short_name": "SS25",
    "start_date": "2025-07-21",
    "stream_url": "https://www.twitch.tv/activeneotokyoplayers",
    "bracket_url": "https://scheduler.leaguelobster.com/2275706/summer-skirmish/2025/",
    "vods_url": "https://www.youtube.com/@ActiveNeotokyo",
    "equal_bans": True, # equal number of map bans per team
    "maps_per_match": 3, # number of maps in a single match
    "max_bans": 1, # maximum number of maps banned per team
    "max_picks": 1, # maximum number of maps picked per team
    "map_pools": ["Standard", "Wildcard"] # list of available map pools
}

# List of available maps with versions, aliases, and map pool types
MAPS = {
    "Envoy": {
        "version": "nt_envoy_ctg",
        "aliases": [],
        "pool": "Standard",
    },
    "Oilstain": {
        "version": "nt_oilstain_ctg",
        "aliases": ["Oil"],
        "pool": "Standard",
    },
    "Rogue": {
        "version": "nt_rogue_ctg_b4",
        "aliases": [],
        "pool": "Standard",
    },
    "Scrapmetal": {
        "version": "nt_scrapmetal_ctg_a7f",
        "aliases": ["Scrap"],
        "pool": "Standard",
    },
    "Tetsu": {
        "version": "nt_tetsu_ctg_b6f",
        "aliases": ["Testu"],
        "pool": "Standard",
    },
    "Dawnlife": {
        "version": "nt_dawnlife_ctg_b1",
        "aliases": ["Dawn"],
        "pool": "Wildcard",
    },
    "Tetsujin": {
        "version": "nt_tetsujin_ctg",
        "aliases": ["Jin"],
        "pool": "Wildcard",
    },
    "Turmuk": {
        "version": "nt_turmuk_ctg_beta3",
        "aliases": ["Tarmac"],
        "pool": "Wildcard",
    },
}

# List of teams with role names, clan tags, and role IDs
TEAMS = {
    "Bonkurazu": {
        "role": "[BONK] Bonkurazu",
        "tag": "BONK",
        "id": 915003320081473576
    },
    "DuctTales": {
        "role": "._o< | DuctTales",
        "tag": "._o<",
        "id": 1386762664990212166
    },
    "Equinox": {
        "role": "[EQ] Equinox",
        "tag": "EQ",
        "id": 1386760980029112520
    },
    "KOBAYASHI CLAN": {
        "role": "[KOBA] KOBAYASHI CLAN",
        "tag": "KOBA",
        "id": 1135193320155525171
    },
    "SHOCK AND AWE": {
        "role": "[SAA] SHOCK AND AWE",
        "tag": "SAA",
        "id": 1386763196496609451
    },
    "Slightly Less Incompetent": {
        "role": "=-SLI-= Slightly Less Incompetent",
        "tag": "SLI",
        "id": 1396589635936849920
    },
    "They Will Eat Earl's Dust": {
        "role": "[11:59] They Will Eat Earl's Dust",
        "tag": "11:59",
        "id": 1396589916695040093
    }
}
