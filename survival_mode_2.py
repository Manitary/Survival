#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 19 12:01:46 2017

@author: grkles
"""

import numpy as np
from itertools import combinations
from random import choice

#### Load data files ####
matchup = [1.,2.,0.5]

with open('matchup.csv', encoding='utf-8') as f:
    dat = [line.strip('\n') for line in f.readlines()]
    TYPE_CHART = np.zeros((18,18), dtype=float)
    TYPE_ORDER = dat[0].split(',')[1:]
    for i, line in enumerate(dat[1:]):
        t2, *match = line.split(',')
        TYPE_CHART[i] = [matchup[int(m)] for m in match]

with open('stages.txt', encoding='utf-8') as f:
    ALL_STAGES = [None] #stages are 1-indexed
    for i,line in enumerate(f.readlines()):
        dat = line.strip('\n').split(' ')
        snum, name, typ, hp, pokenum = dat
        ALL_STAGES.append({"#":int(snum), "n":name, "t":typ.capitalize(),
                           "hp":int(hp), "p#":int(pokenum)})

STAGE_TYPES = np.array([-1] + [TYPE_ORDER.index(stage['t']) for stage in ALL_STAGES[1:]])
STAGE_HPS = np.array([-1] + [stage['hp'] for stage in ALL_STAGES[1:]])
                           
with open('pokes.txt', encoding='utf-8') as f:
    POKES = {}
    MEGAS = {}
    for line in f.readlines():
        poke = line.strip('\n').split(' ')
        
        if poke[-1] == "Mega":
            MEGAS[poke[0]] = poke
        else:
            POKES[poke[0]] = poke

POKE_ORDER = sorted(POKES.keys())
POKE_ORDER_ARR = np.array(POKE_ORDER)
MEGA_ORDER = sorted(MEGAS.keys())
MEGA_ORDER_ARR = np.array(MEGA_ORDER)

#### Precompute damage values ####

match_chance = {3: 0.75, 4: 0.22, 5: 0.03}
match_multiplier = {3: 1.0, 4: 1.5, 5: 2.0}

po4_activ = {3: 0., 4: 1., 5: 0.}
po4p_activ = {3: 0., 4: 0.8, 5: 0.}
rt_activ = {3: 0.5, 4: 0.7, 5: 1.0}
base_activ = {3: 0., 4: 0., 5: 0.}

rt_mult = (0.83 + 7.5) / 2.
po4_mult = 3.6
po4p_mult = 4.5

def skill_damage(rate, mult, top):
    dmg = 0.
    for match in range(3, top+1):
        sk = rate[match]
        sk_mult = (1 - sk) + mult * sk
        dmg += match_multiplier[match] * sk_mult * match_chance[match]
    return dmg

rt_dmg = skill_damage(rt_activ, rt_mult, 5)
po4_dmg = skill_damage(po4_activ, po4_mult, 4)
po4p_dmg = skill_damage(po4p_activ, po4p_mult, 4)
base_dmg = skill_damage(base_activ, 1., 5)

SKILL_DAMAGE = np.array([rt_dmg, po4_dmg, po4p_dmg, base_dmg])

SKILL_ORDER = ["RT", "Po4", "Po4+", "Mega"]

#get indices into the type chart
poke_types = np.array([TYPE_ORDER.index(POKES[p][1]) for p in POKE_ORDER])
poke_ap = np.array([int(POKES[p][2]) for p in POKE_ORDER])
poke_skill = np.array([SKILL_DAMAGE[SKILL_ORDER.index(POKES[p][3])] for p in POKE_ORDER])

POKE_DAMAGE = (TYPE_CHART[poke_types] * np.tile(poke_ap[:, np.newaxis], (1, 18)) *
               np.tile(poke_skill[:, np.newaxis], (1, 18)))

ALL_TEAMS = np.array(list(combinations(range(len(POKES)), 3)))
N_TEAM = ALL_TEAMS.shape[0]

def team_string(tnum, midx):
    members = [MEGA_ORDER[midx]] + POKE_ORDER_ARR[ALL_TEAMS[tnum]].tolist()
    return ", ".join(members)

TEAM_DAMAGE = POKE_DAMAGE[ALL_TEAMS].sum(axis=1)

#now for megas
mega_types = np.array([TYPE_ORDER.index(MEGAS[p][1]) for p in MEGA_ORDER])
mega_ap = np.array([int(MEGAS[p][2]) for p in MEGA_ORDER])
mega_skill = np.array([SKILL_DAMAGE[SKILL_ORDER.index(MEGAS[p][3])] for p in MEGA_ORDER]) #this is just "base damage"

MEGA_DAMAGE = (TYPE_CHART[mega_types] * np.tile(mega_ap[:, np.newaxis], (1, 18)) *
               np.tile(mega_skill[:, np.newaxis], (1, 18)))

#### Set up SM stages ####

boss = [10, 20, 30, 45, 60, 75, 90, 105, 120, 135, 150]

def genstage(start, stop=None, chosen=None):
    if not stop:
        return [start]
    return [i for i in range(start,stop+1) if i not in boss + chosen]


survival = ([(1,5), (6,9), (10,)] + [(11,19)]*2 + [(20,)] + 
            [(22,44)]*3 + [(30,), (45,)] + [(31,74)]*3 + [(103,), (31,74), (90,)] + 
            [(76,89)]*2 + [(75,)] + [(1,74)]*2 + [(46,74)]*4 + [(60,)] + 
            [(90,119)]*2 + [(120,), (1,104)] + [(76,104)]*2 + 
            [(129,131)]*3 + [(1,119)] + [(76,119)]*2 + [(105,), (1,134)] +
            [(121,134)]*3 + [(135,), (1,148)] + [(136,148)]*3 + [(150,)])

def get_sm_stages():
    chosen = []
    for stage in survival:
        available = genstage(*stage, chosen=chosen)
        new_stage = choice(available)
        chosen.append(new_stage)
    return chosen

#### Efficiency calculation ####

def efficiency(stage_nums, team, mega):
    """
    New & improved: use the magic numpy array indexing to figure out all
    stages at the same time for a given team + mega.
    """
    
    stypes = STAGE_TYPES[stage_nums]
    shps = STAGE_HPS[stage_nums]
    
    avg_damage = (TEAM_DAMAGE[team][stypes] + MEGA_DAMAGE[mega][stypes]) / 4.
    team_eff = shps / avg_damage
    
    return team_eff.sum()

#### Simulator ####

def mc(n=1000, mega='Beedrill'):
    eff = np.zeros((N_TEAM, n), dtype=float)
    
    mega_idx = MEGA_ORDER.index(mega)
    
    for i in range(n):
        stages = get_sm_stages()
        for team in range(N_TEAM):
            eff[team,i] = efficiency(stages, team, mega_idx)
    
    return eff

def stats(eff):
    n = eff.shape[1]
    means = eff.mean(axis=1)
    stds = eff.std(axis=1)
    conf = 1.96 * stds / np.sqrt(n)
    
    return np.vstack((means, conf)).T

if __name__ == "__main__":
    midx = MEGA_ORDER.index('Beedrill')
    
    eff = mc()
    final = stats(eff)
    
    #sort the result based on mean:
    sfinal = np.argsort(final[:,0])
    
    print("Best 10 teams:")
    for team in sfinal[:10]:
        m, c = final[team]
        print("{}: {:6.2f}\u00B1{:4.2f}".format(team_string(team, midx), m, c))
    
    print("Worst 5 teams:")
    for team in sfinal[-5:]:
        m, c = final[team]
        print("{}: {:6.2f}\u00B1{:4.2f}".format(team_string(team, midx), m, c))