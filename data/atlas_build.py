#!/usr/bin/env python3
"""
Reading Atlas builder for Chaos Console.

Reads data/readwise_cache.json (written by readwise_loader.py), scores every
passage against a weighted lexicon for sixteen themes, and writes
data/reading_atlas.json — the file /readwise-highlights/ renders.

    python3 data/atlas_build.py            # build
    python3 data/atlas_build.py --stats    # build and print a theme table

Method (deterministic, so a monthly re-run stays comparable):
  * onboarding boilerplate and reference books in EXCLUDE_TITLES are dropped,
    as are highlights with no text; identical passages are de-duplicated
  * each passage is scored per theme: every distinct STRONG term it contains
    counts 3, every distinct SUPPORT term counts 1
  * a passage is assigned up to three themes whose score clears BAR, best first
  * a link between two themes means they co-occur in at least LINK_MIN passages
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_PATH = SCRIPT_DIR / "readwise_cache.json"
OUT_PATH = SCRIPT_DIR / "reading_atlas.json"

EXCLUDE_TITLES = {
    "How to Use Readwise",
    "The Great Book of American Idioms",
}

STRONG_W = 3
SUPPORT_W = 1
BAR = 3
MAX_THEMES = 3
LINK_MIN = 3
TOP_BOOKS = 40
NODE_BOOKS = 12

# ---------------------------------------------------------------------------
# Lexicon. Single tokens match whole words; entries with a space match as a
# phrase. Order of THEMES is the tie-break when scores are equal.
# ---------------------------------------------------------------------------

THEMES = [
    "Power & Political Order",
    "Religion & Belief",
    "War & Mass Violence",
    "Capitalism & Inequality",
    "Nationalism & Civilization",
    "Empire & Geopolitics",
    "Democracy & Law",
    "Cognition & Storytelling",
    "Science & Cosmos",
    "Revolution & Social Change",
    "Language & Literature",
    "Human Nature & Morality",
    "Technology & Media",
    "Race, Caste & Identity",
    "Totalitarianism & Complicity",
    "Memory & History",
]

LEXICON = {
    "Power & Political Order": {
        "strong": """aristocracy, aristocratic, aristocrats, authoritarian, authority, bureaucracy, centralization,
            centralized, clientelism, clientelistic, dynastic, dynasties, elites, feudal,
            feudalism, governance, hierarchical, hierarchies, illegitimate, legitimacy,
            legitimate, monarch, oligarchs, patrimonialism, patronage, political decay,
            political order, queen, regime, regimes, ruling class, sovereign, sovereignty,
            strong state, warlord, warlords, weak states""",
        "support": """administration, administrative, anarchy, coercion, corruption, decay, elite, emperor, emperors,
            faction, factions, govern, governed, government, governments, hierarchy,
            institution, institutional, institutions, leader, leaders, leadership, modern,
            modernity, monarchy, nobility, nobles, obedience, oligarchy, power, powerful,
            powers, rule, ruled, ruler, rulers, rules, ruling, stability, state, state building,
            states, system, taxation, taxes, throne""",
    },
    "Religion & Belief": {
        "strong": """atheism, atheist, atheists, believer, believers, biblical, blasphemy, buddhism, buddhist,
            christian, christians, churches, clergy, crusades, deities, divine, divinity,
            doctrine, doctrines, evangelical, evangelicals, faith, faiths, fundamentalist,
            heresy, heretic, heretics, hindu, hinduism, ideology, islam, jewish, judaism,
            miracle, miracles, missionaries, monasteries, monastery, monk, monks, monotheism,
            monotheistic, mosque, mosques, orthodox, pagan, pagans, pilgrims, polytheism, pray,
            prayers, prophet, prophets, protestants, quran, rabbis, religion, religions,
            religious, resurrection, sacred, salvation, scripture, scriptures, sect, sects,
            secularism, supernatural, synagogue, talmud, theologians, theological, theology,
            worship, worshipped""",
        "support": """afterlife, belief, beliefs, bible, christianity, church, confession, congregation, devout,
            dogma, dogmatic, eternal, fanatic, fanatics, fundamentalism, god, gods, hell, holy,
            islamic, jerusalem, jesus, martyr, martyrs, muslim, muslims, palestine, palestinian,
            priests, revelation, ritual, saint, saints, secular, sin, sinful, souls, spiritual,
            superstition, superstitious, traditions, values""",
    },
    "War & Mass Violence": {
        "strong": """airstrike, ambush, armies, armistice, army, artillery, atrocities, atrocity, auschwitz,
            battlefield, bayonet, beheaded, besieged, blitzkrieg, bombed, camp, casualties,
            ceasefire, cleansing, concentration camp, concentration camps, conscription,
            conscripts, corpse, death camp, death camps, death march, deportation, deportations,
            deported, einsatzgruppen, ethnic cleansing, expulsion, expulsions, exterminated,
            extermination, famine, front line, frontline, gassed, genocidal, genocide, grenade,
            grenades, gulag, holocaust, invaded, invading, invasion, killings, lynched,
            lynching, machine gun, machine guns, mass grave, mass graves, massacre, massacres,
            militia, militias, mobilized, murdered, occupiers, offensive, partisans, pogrom,
            pogroms, prisoner, prisoners, raped, rapes, red army, refugee, refugees, regiment,
            regiments, shot dead, siege, soldier, soldiers, ss men, starvation, starve, starved,
            starving, surrendered, tanks, towns, treblinka, trench, trenches, troops, veteran,
            war crimes, wehrmacht, wounded""",
        "support": """allied, battle, bloody, bombs, camps, captured, cities, civilian, dead, death, deaths, defeated,
            destruction, died, displaced, eastern front, enemy, expelled, front, generals,
            gestapo, headquarters, hitler, horrors, hundreds, hunger, june, killed, military,
            mobilization, murders, nazi, nazis, nkvd, occupation, officers, population,
            populations, rape, retreat, ruins, russians, slaughtered, soviet, soviets, ss,
            stalin, survivors, ukraine, ukrainians, vengeance, veterans, village, villages,
            wars, wartime, winter, women""",
    },
    "Capitalism & Inequality": {
        "strong": """bailouts, bankers, banking, banks, billionaire, billionaires, capitalism, capitalist,
            capitalists, commerce, commercial, consumers, corporate, creditors, deregulation,
            dividends, economies, economists, employer, employers, entrepreneurial, finance,
            free market, free markets, incentive, incentives, income, incomes, industrialists,
            inequalities, insurance, investment, landlords, lobby, lobbying, lobbyists, market,
            markets, marxism, marxist, merchant, millionaires, monopolies, monopolistic,
            monopoly, mortgage, mortgages, pension, pensions, plutocracy, plutocrats, poverty,
            productive, productivity, profit, profitable, profits, recession, redistribution,
            salaries, salary, shareholder, subsidy, supply and demand, tariff, tariffs, tax,
            taxes, trade, upper class, wage, wealth, wealthiest, wealthy, worker""",
        "support": """agriculture, business, businesses, businessmen, buy, buying, classes, coinage, coins, communism,
            companies, cost, dollar, dollars, economic, economics, economy, employees, estates,
            farmers, farms, financial, fortunes, greedy, growth, industry, investments, labour,
            luxury, marketplace, money, owned, ownership, payment, peasants, poor, price,
            prices, property, prosperity, rich, richest, services, spend, taxpayers, unemployed""",
    },
    "Nationalism & Civilization": {
        "strong": """asian values, assimilated, assimilation, chauvinism, chauvinist, civilisation, civilisations,
            civilization, civilizational, civilizations, civilized, clash of
            civilizations, confucianism, cosmopolitan, cosmopolitanism, cultural identity,
            decline of the west, ethnic nationalism, eurocentric, fatherland, fault lines,
            homeland, islamic civilization, kin country, kin-country, modernisation,
            modernization, motherland, nation state, nation-state, nation-states, national
            consciousness, national identity, nationalism, nationalist, nationalistic,
            nationalists, nationality, nationhood, orthodox civilization, patriotism, patriots,
            self-determination, sinic, the west, traditions, universal civilization,
            universalism, western, western civilization, westerners, westernisation,
            westernization, westernized, xenophobia, xenophobic""",
        "support": """barbarians, barbarism, christian, civilized, cultural, culture, cultures, customs, european,
            fault line, heritage, indigenization, indigenous, inferior, japanese, languages,
            muslim, muslims, neighbors, ottoman, ottomans, resurgence, revival, russian,
            superior, superiority, traditional, turkish, turks, unified, unify, values, west""",
    },
    "Empire & Geopolitics": {
        "strong": """alliance, ambassadors, annex, annexation, annexed, arms race, balance of power, bismarck,
            border, brezhnev, buffer state, colonies, colonists, colonized, conquering,
            conqueror, conquerors, conquest, containment, detente, deterrence, diplomacy,
            détente, envoys, exceptionalism, expansionism, expansionist, foreign policy,
            geopolitical, geopolitics, gorbachev, great power, great powers, hegemon, hegemonic,
            hegemony, imperialism, international order, international system, intervention,
            interventionist, interventions, isolationism, isolationist, kissinger, league of
            nations, manifest destiny, metternich, middle kingdom, monroe doctrine, nato,
            negotiation, negotiations, nixon, nuclear weapons, opium war, opium wars,
            partitioned, peace of westphalia, protectorate, raison d'état, realpolitik, silk
            road, sphere of influence, spheres of             influence, statecraft, statesman,
            statesmen, superpower, superpowers, treaties, treaty, tributary, tribute, vassal,
            vassals, westphalia, westphalian, world order, zhou enlai""",
        "support": """alliances, austria, austrian, borders, china, chinese, colonial, czar, defeat, diplomatic,
            dynasties, dynasty, emperors, empire, equilibrium, european, foreign, habsburg,
            habsburgs, independence, indian, international, iranian, japan, kingdom, korea,
            kremlin, mao, moscow, order, peace, peking, persia, powers, prussian, russia,
            russian, sovereign, sovereignty, strategies, territorial, territory, throne, united
            states""",
    },
    "Democracy & Law": {
        "strong": """amendment, autocrat, ballot, ballots, campaign, campaigns, candidate, candidates, checks and
            balances, citizenship, clientelism, congress, congressional, constitution,
            constitutions, corrupt, corrupted, corruption, courts, defendant, defendants,
            demagogue, demagoguery, demagogues, democracies, democracy, democrat, democratic,
            democratization, democratizing, democrats, election, elections, electoral,
            electorate, executive branch, filibuster, free press, free speech, freedoms,
            gerrymandering, governors, human             rights, illiberal, impeach,
            impeachment, incumbent, incumbents, judicial, judiciary, juries, lawyer,
            legislation, legislative, legislator, legislators, legislature, legislatures,
            liberal democracies, liberal democracy, majority rule, mayor, mayors, minority
            rights, partisanship, political party, polling, polls, populists, presidency,
            presidential, prosecutor, prosecutors, referendum, representative government,
            representatives, republican, republicans, republics, rule of law, senate, senator,
            senators, separation of powers, statute, statutes, suffrage, supreme court, trials,
            tyranny of the majority, verdict, voter, voters""",
        "support": """autocracy, biden, bill, bills, bipartisan, capitol, clinton, coalition, coalitions, court,
            federal, judges, justice, law, legitimacy, liberal, lincoln, majority, minority,
            offices, parliamentary, parties, party, political parties, politician, prosecution,
            protests, public opinion, reagan, reform, reforms, representation, rights, senate,
            votes, voting""",
    },
    "Cognition & Storytelling": {
        "strong": """anchoring, bias, biases, brains, cognition, cognitive, conscious, consciousness, decision-
            making, delusion, delusional, delusions, dreaming, ego, fast thinking, fictional,
            fictions, framing, gossip, gossiping, hallucination, heuristic, heuristics,
            illusions, imaginary, imagined order, imagined orders, imagined realities, imagined
            reality, instinctive, instincts, intersubjective, intuitions, intuitive,
            intuitively, irrationality, memories, mentally, minds, mythologies, mythology,
            myths, narrative, narratives, neural, neuron, neurons, neuroscience, objective
            reality, overconfidence, overconfident, perceptions, primed, priming, self-
            deception, sense-making, shared fictions, shared myths, slow thinking, storyteller,
            storytellers, storytelling, subconscious, system 1, system 2, thinker""",
        "support": """abstraction, animal, awareness, beliefs, biased, errors, expectations, explanation, false,
            fools, illusion, imagined, insight, instinct, invented, judgement, lies, predict,
            sapiens, story, survival, telling, thinking, thought, trick, tricks, uncertainty,
            unconscious""",
    },
    "Science & Cosmos": {
        "strong": """acceleration, adaptations, algebra, alien life, andromeda, antimatter, asteroid, asteroids,
            astronaut, astronauts, astronomer, astronomers, astrophysicist, astrophysicists,
            astrophysics, atom, atoms, bacteria, bacterium, big bang, biologist, biologists,
            black hole, black holes, carbon, cell, cells, chemically, chemist, chimpanzee,
            climate, comet, comets, copernicus, cosmic, cosmological, cosmology, dark energy,
            dark matter, darwin, dinosaur, dinosaurs, dna, ecosystem, ecosystems, entropy,
            equation, evolution, evolutionary, exoplanet, exoplanets, expansion             of
            the universe, experimental, experiments, extinct, extraterrestrial, fossils,
            galaxies, galaxy, galileo, gene, genetic, genetics, genome, geological, geology,
            geometry, gravitational, gravity, helium, homo erectus, hubble, hydrogen,
            hypothesis, ice age, kepler, laboratory, light years, light-year, light-years,
            mammal, mathematician, mathematicians, mathematics, mercury, microscope, microwave,
            milky way, molecular, molecule, molecules, mutation, mutations, nasa, natural
            selection, neanderthal, nebula, nebulae, neutron, neutrons, newton, nitrogen,
            nucleus, observable universe, orbit, orbiting, orbits, organism, organisms,
            particle, particles, photon, physicist, physicists, planet, planetary, planets,
            pluto, primate, primates, proton, protons, quantum, radiation, radioactive,
            relativity, rocket, rockets, solar             system, spacecraft, spacetime, speed
            of light, star, stars, stellar, supernova, supernovae, tectonic, telescopes,
            temperature, temperatures, theoretical, thermodynamics, universe, vacuum, velocity,
            venus, virus, viruses, wavelength, wavelengths, x-ray""",
        "support": """atomic, billion, biology, chemical, cosmos, density, discovered, discovery, distances, earth,
            element, elements, energy, evolves, experiment, extinction, freezing, gas, gases,
            genes, heat, jupiter, light, liquid, mars, mathematical, matter, measured,
            measurement, measurements, melting, momentum, moons, night sky, observations,
            oxygen, photons, physics, pressure, scientific, scientists, sizes, solar, solid,
            space, sun, theories, trillion, trillions, visible, wave, weight""",
    },
    "Revolution & Social Change": {
        "strong": """abolished, abolition, abolitionist, abolitionists, agricultural revolution, american revolution,
            ancien regime, ancien régime, barricade, barricades, bolshevik, breakthroughs,
            cognitive revolution, counterculture, coup, coups, disrupt, disruption, emancipated,
            emancipation, epoch, epochal, era, eras, french revolution, glorious revolution,
            guillotine, industrial revolution, insurrection, insurrections, jacobins,
            manifestos, mob, mobilized, mobs, new era, old order, old regime, overthrew,
            overthrow, overthrown, progressives, protest, protesters, protestors, protests,
            radical, radicalism, radicalized, radicals, rebel, rebellions, rebels, reform,
            reformation, reformer, reformers, reforms, renaissance, revolution, revolutionaries,
            revolutionary, revolutions, riot, rioting, robespierre, russian revolution,
            scientific revolution, seismic, strikers, strikes, suffragette, suffragettes,
            tipping point, trade union, trade unions, transformation, transformations,
            transformative, trotsky, tumult, tumultuous, turmoil, upheaval, upheavals, uprising,
            uprisings, utopias""",
        "support": """changes, decade, discovery, dramatically, dynamics, era, fallen, farming, gradual, hunter
            gatherers, hunter-gatherers, ideologies, industrial, invention, modernity, momentum,
            movements, nomadic, nomads, overnight, printing, railways, rebellion, rebuild,
            remade, replace, replacing, reshaped, revolt, risen, settled, shifts, sudden,
            tensions, tide, transitions, urbanization""",
    },
    "Language & Literature": {
        "strong": """accent, accents, albanian, alphabet, alphabets, austen, authorship, autobiography, best-seller,
            best-sellers, bestseller, bestsellers, biographies, blank page, bookshop, bookshops,
            bookstore, bookstores, borges, calvino, cantonese, chekhov, cliche, cliches, cliché,
            clichés, comedian, comedians, consonant, consonants, critic, curse, cursing, dante,
            dialect, dialects, dialogues, dickens, dictionaries, dictionary, dostoevsky,
            dostoyevsky, drafts, edited, editing, editor, editors, essayist, faulkner, first
            draft, flaubert, french language, german language, grammar, grammatical,
            handwriting, hebrew, hemingway, homer, humorous, humour, idiom, idioms, illiteracy,
            illiterate, ironic, jargon, joyce, kafka, linguist, linguistic, linguistics,
            linguists, literacy, literary, literary criticism, literature, mandarin, manuscript,
            manuscripts, memoir, memoirs, metaphor, metaphorical, metaphors, mispronounced,
            monologue, nabokov, narration, narrator, narrators, non-fiction, nonfiction, novel,
            novelist, novelists, novels, orwell, paragraph, paragraphs, pen, pencil, pessoa,
            phrasing, plot, plots, poems, poet, poetry, polish language, portuguese, profanity,
            pronounce, pronounced, pronunciation, prose, prose style, protagonist, proust,
            publisher, publishers, publishing, pun, punctuation, puns, readers, reading list,
            reads, reviewer, reviewers, revisions, rewrite, rewriting, rewrote, rhyme, rhymes,
            rhythm, russian language, saramago, satire, satirical, sentence, simile, similes,
            slang, speaks, spelled, spelling, spoken, steinbeck, stylistic, swearing, syllable,
            syllables, syntax, textual, tolstoy, translate, translated, translation,
            translations, translator, translators, typewriters, verse, vocabularies, vocabulary,
            vowel, vowels, witty, wordplay, writings""",
        "support": """actor, artistic, artists, arts, chapter, classroom, describe, description, draft, exam, exams,
            films, homework, language, legend, legends, lessons, listen, listened, listening,
            meanings, misunderstand, misunderstanding, naming, phrases, poetic, read, reading,
            review, reviews, scenes, script, scripts, sentences, silence, silent, singing,
            songs, spanish, speak, speaking, stage, tale, tales, theatre, title, titles, words,
            write, writer, written""",
    },
    "Human Nature & Morality": {
        "strong": """absurd, altruistic, amoral, appetite, appetites, aristotle, ashamed, atone, atonement, banality
            of evil, benevolence, benevolent, betrayal, better angels, blameless, camus,
            categorical imperative, charitable, charity, compassion, conscience, consciences,
            conscientious, contemptuous, coward, cowardly, cruelties, cruelty, dark side,
            decency, deserve, determinism, determinist, dignity, disgust, disgusting, dishonest,
            dishonesty, dishonor, dishonour, disloyal, disposition, duties, empathetic, empathy,
            envious, epicurean, ethical, ethically, ethics, evils, existential, existentialism,
            existentialist, flawed, forgave, generosity, gentleness, gluttony, golden rule, good
            and bad, goodness, greedy, guilt, guilty, hates, honest, honesty, honour,
            honourable, human nature, humiliate, humiliating, humiliation, hypocrite,
            hypocrites, hypocritical, immorality, impatient, imperfect, imperfection, inhumane,
            innocence, innocent, intolerance, intolerant, irresponsible, kant, kantian,
            kindness, loving, merciful, mistrust, morality, morals, nihilism, nihilist, ordinary
            man, passions, patience, patient, prejudice, punishment, redeem, redeemed,
            redemption, regrets, remorse, remorseful, remorseless, repent, repentance, right and
            wrong, righteous, righteousness, saint, saintly, scruples, scrupulous, self
            interest, self-interest, self-righteous, selfishness, shame, sin, sinful, sinner,
            sinners, sloth, socrates, stoic, stoicism, stoics, temperament, temptations,
            tempted, tenderness, the banality of evil, tolerant, trusting, unethical,
            unfairness, utilitarian, utilitarianism, vices, virtue, virtue ethics, virtues,
            wicked, wickedness, wrongdoer, wrongdoing""",
        "support": """bystander, bystanders, commanded, conform, disobedience, disobey, evil, fears, fragile,
            fragility, fury, greed, grief, heal, healing, helpless, hopeful, hopeless, husband,
            immoral, intend, intentions, joyful, judge, killing, lesson, lessons, liars,
            malevolent, morally, motivated, motive, mourn, mourning, murderer, neighbor,
            neighbour, obeyed, peer, perpetrator, perpetrators, persons, resent, resilient,
            sister, souls, spite, spiteful, stole, stranger, survived, temptation, thief,
            worried, wounds""",
    },
    "Technology & Media": {
        "strong": """4k, addicted, addiction, addictive, ads, adsense, advertisement, advertiser, ai, algorithm,
            algorithmic, algorithms, altman, amazon, amazon's, android, app, apple, apple's,
            apps, artificial intelligence, attention economy, automate, automated, big data,
            bill gates, bots, brand deal, brand deals, broadcaster, broadcasters, broadcasting,
            cellphone, cellphones, censored, censorship, chatbot, chatbots, chatgpt, chip,
            chips, click, click-through, clickbait, clicks, cloud computing, codec, codecs,
            coder, coders, coding, computational, computer, computing, content creators,
            cookies, creator economy, ctr, cyber, cybersecurity, database, databases, davinci,
            davinci resolve, deep learning, delivery, deplatformed, deplatforming, digital,
            digitization, disinformation, disruptor, disruptors, dorsey, downloaded, drone,
            drones, e-commerce, e-mail, echo chamber, echo chambers, ecommerce, edited, editor,
            electrical, elon musk, emails, encrypted, encryption, engagement, engagement
            metrics, engineering, engineers, facebook, facebook's, filming, filter bubble,
            filter bubbles, follower, footage, founder, frame rate, frames, gates, gig economy,
            gig workers, google, google's, growth hacking, gutenberg, hacked, hacker, hackers,
            hacking, hardware, hd, hollywood, influencer, influencers, innovate, innovator,
            instagram, internet, iphone, iphones, ipo, jack dorsey, keyword, laptop, laptops,
            larry page, late night, late-night, machine learning, mark zuckerberg, membership,
            messaging, meta, microchip, microchips, microsoft, misinformation, mobile,
            moderation, moderators, monetize, monetized, monopolies, nadella, netflix,
            networked, neural network, neural networks, news media, newsfeed, newsroom,
            notification, notifications, offline, online, peter thiel, pichai, platform,
            platforms, podcast, podcasts, polarized, premiere, prime time, primetime, printing
            press, producer, producers, programmer, programmers, programming, reality
            television, reality tv, reddit, regulated, regulators, rendering, reporters, robot,
            robotic, robotics, sam altman, sandberg, satellites, scroll, scrolling, section 230,
            semiconductor, semiconductors, seo, sergey brin, server, servers, sheryl sandberg,
            silicon, silicon valley, sitcom, sitcoms, smartphones, snapchat, social media,
            social network, social networks, software, spacex, sponsorship, sponsorships, start-
            up, start-ups, startup, startups, streamed, streaming, studios, subscription,
            subscriptions, surveillance, tablet, tablets, talk shows, techies, technologist,
            technologists, telegraph, telephones, tesla, text message, text messages, texting,
            thiel, thumbnail, tiktok, tracked, tracking, transistors, tweet, tweeted, twitter,
            uber, unicorn, unicorns, upload, uploaded, users, valley, vc, vcs, venture capital,
            venture capitalists, videos, viewership, viral, virality, watch time, wikipedia""",
        "support": """analytics, applications, bezos, bot, campus, communications, companies, computers, connect,
            connections, consumer, customer, cutting-edge, design, designer, designers, devices,
            disruptive, edit, exponential, faster, features, final cut, final cut pro, fired,
            founders, futuristic, hire, hiring, innovation, innovators, interface, invention,
            inventor, jeff bezos, laid off, layoffs, marketplace, mass media, messages,
            modeling, network, newest, openai, photographer, photographers, photography, photos,
            pictures, post, posting, posts, pr, product, profit, promotion, public relations,
            release, revenues, robots, scaled, scaling, sell, sharing, simulated, simulation,
            speed, spin, state-of-the-art, steve jobs, tools, update, updates, upgrade,
            upgraded, user, valuation, website""",
    },
    "Race, Caste & Identity": {
        "strong": """aboriginal, aborigines, affirmative action, african american, african-american, african-
            americans, africans, afrikaans, afrikaner, afrikaners, ancestral, ancestry, anti-
            semite, antisemite, antisemites, antisemitic, apartheid, apartheid
            government, aryan, aryans, assimilate, assimilated, bantu, bigot, bigotry, biracial,
            birmingham, blackness, blacks, bloodline, bloodlines, boer, boers, booker t.
            washington, born into, brahmin, brahmins, caste, castes, civil rights, civil rights
            movement, class system, color-blind, colorblind, colored, colored people, coloured,
            coloured people, dalit, dalits, dehumanization, dehumanizing, diaspora,
            discriminate, discriminated, discrimination, discriminatory, dominant caste, du
            bois, emigrants, emigration, endogamy, enslavement, ethnic, ethnically, ethnicities,
            ethnicity, eugenic, eugenics, exiles, foreigner, frederick douglass, freedom riders,
            ghettoes, ghettos, group areas, hyphenated, hyphenated american, hyphenated
            americans, impure, indians, inferior race, insiders, integrate, integrated,
            intermarriage, isabel wilkerson, jew-hatred, jim crow, johannesburg, king jr,
            lineage, lineages, lower caste, lower class, lynch, lynched, lynching, malcolm x,
            marginalised, marginalization, master race, migrant, migrants, migration,
            miscegenation, mixed race, mixed-race, montgomery, mulatto, multicultural, native,
            native american, native americans, negro, negroes, noah, nuremberg law, nuremberg
            laws, oppressed, oppressor, oppressors, otherness, outsider, outsiders, pale of
            settlement, pass laws, pollution, prejudice, prejudiced, racial, racially, racism,
            racist, racists, ranking, rosa parks, segregated, segregation, segregationist,
            selma, skin color, skin colour, slaveholder, slaveholders, slaveholding, slavery,
            social class, south africa, south african, stranger, stratification, stratified,
            subhuman, subhumans, subjugated, subordinate, subordinate caste, subordinated,
            subordination, supremacist, supremacists, township, townships, trevor noah,
            tribalism, tribes, untouchable, untouchables, upper caste, upper class, w.e.b. du
            bois, white supremacy, whiteness, wilkerson, xenophobia, xenophobic, xhosa, zulu""",
        "support": """africa, albanian, albanians, armenian, armenians, asians, balkan, balkans, belonging, bosnia,
            bosnian, boxes, categorized, category, citizenship, clan, clans, classes, color,
            colour, croatian, dark-skinned, dignity, diverse, divides, faces, fair-skinned,
            filipino, greeks, gypsies, gypsy, hindu, hispanic, hispanics, humiliation, hutu,
            hutus, identities, immigrants, inferior, insulted, insults, intermarry, italians,
            japanese, kinship, kosovo, kurdish, kurds, latino, latinos, lighter, marry, mixing,
            nationalities, nationality, protestants, roma, rwandan, slur, slurs, stereotype,
            stereotyped, stereotypes, stigma, stigmatized, them and us, tribe, turkish, tutsi,
            tutsis, ukrainian, ukrainians, unequal, us and them, vietnamese, white, whites""",
    },
    "Totalitarianism & Complicity": {
        "strong": """absolute control, absolute power, apparatchik, apparatchiks, apparatus, aryan, aryans, at
            gunpoint, atomization, atomized, banality of evil, beria, blackmail, blackmailed,
            blackshirts, blocking detachments, blood and soil, brownshirts, buchenwald,
            bureaucrat, bureaucrats, bystander, bystanders, careerism, careerist, careerists,
            censor, censored, censors, censorship, central committee, chain of command, class
            enemies, class enemy, clerk, coerced, cog, cogs, collaborate, collaborated,
            collaboration, collaborator, collaborators, collective guilt, collective punishment,
            collective responsibility, collectivisation, commissar, commissars, complicit,
            complicit silence, confessions, conform, conformed, conformist, could not have
            known, cover up, cover-up, covered up, covering up, cult, cult of personality,
            cults, dachau, dekulakization, denial, denialism, denier, deniers, denounce,
            denounced, denunciation, denunciations, denying, deportation, deportations, desk
            murderer, desk murderers, dictator, dictatorial, dictators, dossier, dossiers,
            doublethink, enabling act, enemies of the people, enemy of the people, espionage,
            executioner, executioners, fanatic, fanatics, fascist, fascists, fellow travelers,
            fellow travellers, five year plan, five-year plan, following orders, forced
            confession, franco, fuhrer, functionaries, functionary, führer, gears, ghettoes,
            ghettos, gleichschaltung, goering, great purge, great terror, gulag, gulags, gun to
            the head, göring, heil hitler, himmler, holodomor, hostage, hostages, i was only,
            ideologue, ideologues, infallibility, infallible, informant, informants, informer,
            informers, innocence, innocent, interrogated, interrogation, interrogations,
            interrogator, interrogators, intimidated, intimidation, judenrat, just following
            orders, kapo, kapos, kgb, kirov, kolyma, kristallnacht, kulak, kulaks, labor camp,
            labor camps, labour camp, labour camps, leader worship, lebensraum, leninism,
            leninist, look away, looked away, looking away, loyalty oath, loyalty oaths,
            lubyanka, marxist-leninist, mass rallies, mass rally, master race, mein kampf,
            membership card, molotov, monuments, mussolini, must have known, nazi, nazism,
            newspeak, night of the long knives, nkvd, nomenklatura, not one step back, nuremberg
            rallies, nuremberg rally, oath, oaths, obedient, obey, obeyed, omniscient, one party
            state, only following orders, opportunism, opportunist, opportunists, order 227,
            order police, ordinary germans, orwellian, paper shufflers, parade, parades, party
            line, party member, party members, peer pressure, penal battalion, penal battalions,
            perpetrator, perpetrators, personality cult, plausible deniability, pledge, police
            state, politburo, political officer, political officers, portrait, portraits,
            poster, posters, prison camp, prison camps, propaganda, propagandist, propagandists,
            purge, purged, purges, rallies, rally, reichstag fire, reprisal, reprisals,
            revisionism, revisionist, revisionists, sa, sachsenhausen, saluted, secret files,
            secret police, should have known, show trial, show trials, siberia, sieg heil,
            silenced, silencing, single-party, slogan, smersh, sobibor, speer, spied, spies,
            spying, stalin, stalin's, stalinist, stasi, statue, storm troopers, stormtroopers,
            subordinate, subordinates, superior officer, surveillance state, swastika,
            swastikas, terrified, terror apparatus, terrorised, terrorized, thought police,
            thoughtcrime, tortured, torturer, torturers, total control, total war, totalitarian,
            totalitarianism, totalizing, treblinka, triumph of the will, trotsky, true
            believer, true believers, turned a blind eye, tyrant, uniforms, useful idiots, volk,
            volksgemeinschaft, wannsee, watchers, we were only, whitewash, whitewashed,
            whitewashing, wilful blindness, wilful ignorance, willful blindness, willful
            ignorance, willing executioners, worship of the leader, yezhov, yezhovshchina,
            zealot""",
        "support": """apparatus, arrests, assassin, assassinate, assassinated, assassination, assassins, banner,
            bribe, bribed, bribery, bunkers, cabbage, cell, cells, checkpoint, checkpoints,
            cigarettes, clandestine, conspiracies, conspirator, conspirators, coup, coups,
            cyanide, deportee, dictatorship, dissenting, dissident, emigres, executed,
            executions, exile, exiles, feared, fence, fences, forced labor, forced labour,
            freed, guard, guards, gun, hanged, hanging, hitler youth, hitler's, hunger,
            imprisoned, imprisonment, jailed, kremlin, liberation, machine, machinery, moscow,
            nazis, nomenklatura, obedience, passport, passports, pistol, pistols, plot, plots,
            plotted, plotting, poisoned, prisons, privileges, queue, queues, ration, ration
            card, ration cards, rationing, rations, regime, resistance, resister, resisters,
            rifle, rifles, samizdat, secret, secretly, sentenced, shortage, shortages, silent,
            slave labour, smuggled, smuggler, smugglers, smuggling, soviet, spy, ss, starving,
            trial, tribunals, underground, unfree, verdict, vodka, warden, wardens, émigré,
            émigrés""",
    },
    "Memory & History": {
        "strong": """afterwards, aleksandr solzhenitsyn, amery, amnesia, amnesiac, améry, anachronism, anachronistic,
            ancestral, anne applebaum, anniversaries, anniversary, antiquity, antony beevor,
            applebaum, archival, archive, archives, archivist, archivists, artefact, artefacts,
            artifact, artifacts, at that time, autobiographies, autobiography, back then,
            beevor, bibliographies, bibliography, bicentennial, biographer, biographers,
            biographies, boll, braudel, buried, buried past, böll, came to terms, catherine
            merridale, centenary, centennial, chronicler, chroniclers, chronicles,
            chronological, chronologically, chronology, citation, cite, cited, collective
            memory, come to terms, coming to terms, commemorated, commemoration, commemorative,
            confront             the past, confronting the past, contemporaries, contingent,
            correspondence, counterfactual, counterfactuals, cultural memory, curated, curators,
            dated, decade, decades ago, decline and fall, diaries, diarist, diarists, diary,
            dig, digging, documentary, documentation, documented, documents, dug, ehrenburg,
            elie wiesel, epic, epics, epoch, epochs, eras, erase, erasing, erasure, ernst
            jünger, evans, evidentiary, excavated, excavation, excavations, exhibit, exhibition,
            exhibitions, eyewitness, eyewitnesses, fated, fest, figes, folk memory, folklore,
            footnote, footnotes, forgetting, forgot, forgotten history, gibbon, ginzburg, good
            old days, grass, great man theory, great men, gunter grass, günter grass, habermas,
            haffner, harald jähner, heinrich böll, herodotus, hidden history, hillgruber,
            hindsight, hindsight bias, historian, historians, historical memory, historical
            record, historikerstreit, historiographical, historiography, history
            repeats, history book, history books, history repeating, hobsbawm, ian kershaw, ilya
            ehrenburg, in those days, inevitability, inter-war, interwar, jahner, jean améry,
            joachim fest, journals, jubilee, judt, junger, jähner, jünger, keith lowe, kershaw,
            klemperer, kotkin, legacies, legend, legendary, legends, lesson of history, lessons
            of history, levi, livy, machiavelli, mark mazower, mazower, memoir, memoirs,
            memorial, memorials, memories, memory             war, memory culture, memory
            politics, memory wars, merridale, montefiore, monument, monuments, museums,
            mythologised, mythologized, mythology, national memory, newsreel, newsreels, nolte,
            nostalgic, oblivion, official             histories, official history, once upon a
            time, oral             tradition, oral histories, oral history, oral traditions,
            orlando figes, path dependence, path dependency, photos, plutarch, politics of
            memory, portrait, portraits, post-war, posterity, pre-war, precedent, precedents,
            presentism, prewar, primary source, primary sources, primo levi, providence,
            providential, public memory, reckon, reckoned, reckoning, recorded, relic, remarque,
            remembering, remembrance, remembrance culture, renaissance, retrospective, revised,
            revisionism, revisionist, revisionists, rewrite history, rewriting history, rewrote
            history, richard evans, rise and fall, road not taken, robert conquest, saga, sagas,
            sebald, sebastian haffner, secondary source, secondary sources, shalamov, shirer,
            silenced history, since             then, snyder, spengler, stephen kotkin, tacitus,
            teleological, teleology, testimonies, testimony, textbook, textbooks, the old days,
            then and             now, thereafter, those days, thucydides, timothy snyder, tony
            judt, trevor-roper, ullrich, unearth, unearthed, vergangenheitsbewältigung, victor
            klemperer, volker ullrich, w.g.             sebald, whig history, wiesel, william
            shirer, worked through, working through, would have             been""",
        "support": """aftermath, albania, analogies, ankara, antwerp, athens, beginnings, belgrade, breslau, brussels,
            bucharest, budapest, causes, commemorate, compare, comparisons, continuities,
            copenhagen, cracow, crimea, czechoslovakia, danzig, discontinuity, echo, echoed,
            echoes, enduring, eternity, event, explain, fleeting, forever, gdansk, ghost,
            ghosts, grandchild, grandchildren, granddaughter, grandparents, grandson, haifa,
            haunt, haunted, helsinki, homeland, hungary, inherit, inherited, interpretations,
            istanbul, kaliningrad, kaunas, kharkiv, kharkov, kiev, konigsberg, krakow, kraków,
            kursk, kyiv, königsberg, landmark, landmarks, lasting, learnt, lemberg, lessons,
            lodz, lviv, lwow, lwów, lyon, marks, marseille, meanings, milan, milestone,
            milestones, millennium, minsk, naples, newer, newest, nostalgia, odesa, odessa,
            originated, parallels, past, petrograd, photo, postwar, remember, resonance,
            resonated, resonates, results, riga, rostov, rotterdam, rupture, ruptures, sarajevo,
            scar, scarred, scars, sevastopol, shadows, silesia, similarity, smolensk, sofia, st
            petersburg, tales, tallinn, teach, teaches, tehran, temporary, trace, traumatised,
            traumatized, tsaritsyn, turin, twice, vichy, vilna, vilnius, volgograd, warsaw,
            wilno, wounds, wroclaw, youngest, yugoslavia, zagreb, łódź""",
    },
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'’\-\.]*")


def _split_terms(blob: str):
    return [t.strip().lower() for t in blob.replace("\n", " ").split(",") if t.strip()]


def _compile(lexicon):
    """Turn the lexicon into (single-word sets, phrase lists) per theme."""
    out = {}
    for theme in THEMES:
        entry = lexicon[theme]
        comp = {}
        for kind in ("strong", "support"):
            words, phrases = set(), []
            for term in _split_terms(entry[kind]):
                if " " in term:
                    phrases.append(term)
                else:
                    words.add(term)
            comp[kind] = (words, phrases)
        out[theme] = comp
    return out


COMPILED = _compile(LEXICON)


def _normalize(text: str) -> str:
    t = text.lower()
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("—", " - ").replace("–", " - ")
    return t


def _tokens(norm: str):
    toks = set()
    for m in _WORD_RE.finditer(norm):
        w = m.group(0).strip("'.-")
        if not w:
            continue
        toks.add(w)
        if w.endswith("'s"):
            toks.add(w[:-2])
    return toks


def score_text(text: str):
    """Return {theme: score} for a passage."""
    norm = _normalize(text)
    padded = " " + re.sub(r"[^a-z0-9']+", " ", norm) + " "
    toks = _tokens(norm)
    scores = {}
    for theme in THEMES:
        comp = COMPILED[theme]
        s = 0
        for kind, weight in (("strong", STRONG_W), ("support", SUPPORT_W)):
            words, phrases = comp[kind]
            s += weight * len(words & toks)
            for ph in phrases:
                if " " + ph + " " in padded:
                    s += weight
        if s:
            scores[theme] = s
    return scores


def classify(text: str):
    """Return up to MAX_THEMES themes whose score clears BAR, best first."""
    scores = score_text(text)
    order = {t: i for i, t in enumerate(THEMES)}
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], order[kv[0]]))
    return [t for t, s in ranked if s >= BAR][:MAX_THEMES]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def load_corpus(cache: dict):
    """Filter and de-duplicate the cache into the passage corpus."""
    seen = set()
    corpus = []
    for h in cache.get("data", []):
        text = (h.get("text") or "").strip()
        title = (h.get("book_title") or "").strip()
        if not text or title in EXCLUDE_TITLES:
            continue
        key = re.sub(r"\s+", " ", text.lower())
        if key in seen:
            continue
        seen.add(key)
        corpus.append({
            "t": text,
            "b": title or "Unknown source",
            "a": (h.get("author") or "").strip(),
            "cat": h.get("category") or "",
            "d": (h.get("highlighted_at") or "")[:10],
            "id": h.get("id"),
        })
    return corpus


def build(cache: dict) -> dict:
    corpus = load_corpus(cache)
    themed = []
    for p in corpus:
        th = classify(p["t"])
        if th:
            themed.append({**p, "th": th})

    theme_count = Counter()
    theme_books = {t: Counter() for t in THEMES}
    pair_count = Counter()
    book_tot = Counter()
    book_author = {}
    book_themes = defaultdict(Counter)
    by_primary = {t: [] for t in THEMES}

    for p in themed:
        book_tot[p["b"]] += 1
        book_author.setdefault(p["b"], p["a"])
        for t in p["th"]:
            theme_count[t] += 1
            theme_books[t][p["b"]] += 1
            book_themes[p["b"]][t] += 1
        for i in range(len(p["th"])):
            for j in range(i + 1, len(p["th"])):
                a, b = sorted((p["th"][i], p["th"][j]), key=THEMES.index)
                pair_count[(a, b)] += 1
        by_primary[p["th"][0]].append({"t": p["t"], "b": p["b"], "a": p["a"], "th": p["th"], "d": p["d"]})

    tid = {t: i for i, t in enumerate(THEMES)}
    nodes = [{
        "id": tid[t],
        "name": t,
        "count": theme_count[t],
        "books": [{"title": b, "n": n} for b, n in theme_books[t].most_common(NODE_BOOKS)],
    } for t in THEMES]
    links = [{"source": tid[a], "target": tid[b], "weight": w}
             for (a, b), w in sorted(pair_count.items(), key=lambda kv: -kv[1]) if w >= LINK_MIN]

    books = []
    for title, n in book_tot.most_common(TOP_BOOKS):
        th = book_themes[title]
        books.append({
            "title": title,
            "author": book_author.get(title, ""),
            "n": n,
            "dominant": th.most_common(1)[0][0],
            "spread": len(th),
            "themes": dict(th.most_common()),
        })

    dates = sorted(p["d"] for p in corpus if p["d"])
    meta = {
        "total_highlights": len(corpus),
        "themed": len(themed),
        "unthemed": len(corpus) - len(themed),
        "n_books": len({p["b"] for p in corpus}),
        "n_themes": len(THEMES),
        "n_links": len(links),
        "raw_highlights": len(cache.get("data", [])),
        "excluded_titles": sorted(EXCLUDE_TITLES),
        "newest_highlight": dates[-1] if dates else "",
        "source_generated": cache.get("generated", ""),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": {"strong_weight": STRONG_W, "support_weight": SUPPORT_W, "bar": BAR,
                   "max_themes": MAX_THEMES, "link_min": LINK_MIN},
    }
    return {"meta": meta, "nodes": nodes, "links": links, "highlights": by_primary, "books": books}


def main():
    ap = argparse.ArgumentParser(description="Build data/reading_atlas.json from the Readwise cache")
    ap.add_argument("--stats", action="store_true", help="print a theme table after building")
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    if not CACHE_PATH.exists():
        print(f"Missing {CACHE_PATH} — run readwise_loader.py first", file=sys.stderr)
        sys.exit(1)
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    atlas = build(cache)
    Path(args.out).write_text(json.dumps(atlas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    m = atlas["meta"]
    print(f"Atlas: {m['themed']} themed / {m['total_highlights']} passages "
          f"({m['unthemed']} unthemed) · {m['n_books']} sources · {m['n_links']} links → {args.out}")
    if args.stats:
        for n in sorted(atlas["nodes"], key=lambda n: -n["count"]):
            print(f"  {n['count']:4d}  {n['name']}")


if __name__ == "__main__":
    main()
