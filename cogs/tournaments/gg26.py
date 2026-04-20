# Tournament settings
INFO = {
    "full_name": "Ghost Gauntlet 2026",
    "short_name": "GG26",
    "start_date": "2026-03-16",
    "stream_url": "https://www.twitch.tv/activeneotokyoplayers",
    "bracket_url": "https://neotokyo.challonge.com/ghostgauntlet2026",
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
        "version": "ntre_ballistremade_ctg_a26ff",
        "aliases": ["Ballistrade", "Balli"],
        "pool": "Standard",
    },
    "Culvert": {
        "version": "nt_culvert_ctg_b6",
        "aliases": [],
        "pool": "Standard",
    },
    "Grid": {
        "version": "ntre_grid_ctg_b2",
        "aliases": [],
        "pool": "Standard",
    },
    "Oliostain": {
        "version": "ntre_oliostain_ctg_b2",
        "aliases": ["Olio"],
        "pool": "Standard",
    },
    "Rise": {
        "version": "ntre_rise_ctg",
        "aliases": [],
        "pool": "Standard",
    },
    "Rogue": {
        "version": "ntre_rogue_ctg",
        "aliases": [],
        "pool": "Standard",
    },
    "Snowfall": {
        "version": "ntre_snowfall_ctg_b13",
        "aliases": [],
        "pool": "Standard",
    },
}

# List of teams with role names, clan tags, and role IDs
TEAMS = {
    "Accessibility Team": {
        "role": "[ATEAM] Accessibility Team",
        "tag": "ATEAM",
        "id": 1476525500385071105
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
    "KOBAYASHI CLAN": {
        "role": "[KOBA] KOBAYASHI CLAN",
        "tag": "KOBA",
        "id": 1135193320155525171
    },
    "MuteNT Support Cats": {
        "role": "[MTNT] MuteNT Support Cats",
        "tag": "MTNT",
        "id": 1476526838640676935
    },
    "RECON FEET": {
        "role": "[FEET] RECON FEET",
        "tag": "FEET",
        "id": 1135193612116824125
    },
    "TGR Woods": {
        "role": "[PAR] TGR Woods",
        "tag": "PAR",
        "id": 1476526209004208179
    }
}
