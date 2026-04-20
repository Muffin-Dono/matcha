# Tournament settings
INFO = {
    "full_name": "Winter Warzone 2025",
    "short_name": "WW25",
    "start_date": "2025-01-13",
    "stream_url": "https://www.twitch.tv/activeneotokyoplayers",
    "bracket_url": "https://neotokyo.challonge.com/ukyfhwxu",
    "vods_url": "https://www.youtube.com/@ActiveNeotokyo",
    "equal_bans": True, # equal number of map bans per team
    "maps_per_match": 3, # number of maps in a single match
    "max_bans": 1, # maximum number of maps banned per team
    "max_picks": 1, # maximum number of maps picked per team
    "map_pools": ["Standard"] # list of available map pools
}

# List of available maps with versions, aliases, and map pool types
MAPS = {
    "Ballistremade": {
        "version": "nt_ballistremade_ctg_a16",
        "aliases": ["Ballistrade", "Balli"],
        "pool": "Standard",
    },
    "Dew": {
        "version": "nt_dew_ctg_b1",
        "aliases": [],
        "pool": "Standard",
    },
    "Grid": {
        "version": "nt_grid_ctg_b1comp",
        "aliases": [],
        "pool": "Standard",
    },
    "Saitama": {
        "version": "nt_saitama_redux_ctg_a5",
        "aliases": ["Tietama"],
        "pool": "Standard",
    },
    "Snowfall": {
        "version": "nt_snowfall_ctg_b12",
        "aliases": [],
        "pool": "Standard",
    },
    "Tetsu": {
        "version": "nt_tetsu_ctg_b6",
        "aliases": ["Testu"],
        "pool": "Standard",
    },
    "Threadplate": {
        "version": "nt_threadplate_ctg",
        "aliases": ["Thread"],
        "pool": "Standard",
    },
}

# List of teams with role names, clan tags, and role IDs
TEAMS = {
    "Anti-Shaving Club I": {
        "role": "[ASCI] Anti-Shaving Club I",
        "tag": "ASCI",
        "id": 1319293536591413298
    },
    "Anti-Shaving Club II": {
        "role": "[ASCI] Anti-Shaving Club II",
        "tag": "ASCII",
        "id": 1325535639260889209
    },
    "Blood and Thunder": {
        "role": "[BLVD] Blood and Thunder",
        "tag": "BLVD",
        "id": 1325533278513401919
    },
    "Bonkurazu": {
        "role": "[BONK] Bonkurazu",
        "tag": "BONK",
        "id": 915003320081473576
    },
    "Ghost Brigade": {
        "role": "[GB] Ghost Brigade",
        "tag": "GB",
        "id": 915291950893129788
    },
    "Hopgoblins": {
        "role": "[HOP] Hopgoblins",
        "tag": "HOP",
        "id": 1319364385415630940
    },
    "Ikko Ikki": {
        "role": "[Ikko] Ikko Ikki",
        "tag": "Ikko",
        "id": 915001460373225502
    },
    "KOBAYASHI CLAN": {
        "role": "[KOBA] KOBAYASHI CLAN",
        "tag": "KOBA",
        "id": 1135193320155525171
    },
    "Menhera": {
        "role": "[MNHR] Menhera",
        "tag": "MNHR",
        "id": 1139703753130389514
    },
    "Only Some Hammers Allowed": {
        "role": "[OSHA] Only Some Hammers Allowed",
        "tag": "OSHA",
        "id": 1319292531078594592
    }
}
