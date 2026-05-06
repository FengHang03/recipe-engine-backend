from __future__ import annotations

import re


class RegexPatterns:
    EXCEPTIONS = {
        "cod liver oil": "FAT_OIL",
        "fish oil": "FAT_OIL",
        "peanut butter": "FAT_OIL",
        "coconut milk": "FAT_OIL",
        "fish sauce": "PROCESSED",
        "beef broth": "PROCESSED",
        "bone broth": "PROCESSED",
    }

    PROCESSED = re.compile(
        r"\b(sauce|broth|stock|soup|stew|gravy|seasoning|powder|extract|flavor|bouillon|salt|sugar|syrup|honey|molasses)\b",
        re.IGNORECASE,
    )

    FAT_OIL = re.compile(
        r"\b(fish oil|cod liver oil|salmon oil|sardine oil|anchovy oil|herring oil|olive oil|canola oil|coconut oil|peanut oil|sunflower oil|soybean oil|corn oil|sesame oil|safflower oil|grapeseed oil|fat|tallow|lard|ghee)\b",
        re.IGNORECASE,
    )

    ORGAN = re.compile(
        r"\b(liver|kidney|kidneys|heart|spleen|brain|tongue|giblet|gizzard|tripe|stomach|lung|pancreas|thymus|testicle)\b",
        re.IGNORECASE,
    )

    PROTEIN_SHELLFISH = re.compile(
        r"\b(cockle|scallop|snail|squid|shrimp|prawn|crab|lobster|crayfish|octopus|calamari)\b",
        re.IGNORECASE,
    )
    MINERAL_SHELLFISH = re.compile(
        r"\b(oyster|mussel|clam)\b",
        re.IGNORECASE,
    )

    FISH_OILY = re.compile(
        r"\b(salmon|tuna|sardine|mackerel|herring|anchovy|trout|sprat|smelt|pilchard)\b",
        re.IGNORECASE,
    )
    FISH_LEAN = re.compile(
        r"\b(cod|haddock|tilapia|catfish|carp|pollock|flounder|halibut|sole|snapper)\b",
        re.IGNORECASE,
    )

    EGG = re.compile(r"\b(egg|eggs|egg white|egg yolk)\b", re.IGNORECASE)
    SUPPLEMENT_CALCIUM = re.compile(
        r"\b(calcium|carbonate|citrate|gluconate|lactate|phosphate|egg-shell|eggshell)\b",
        re.IGNORECASE,
    )

    MEAT = re.compile(
        r"\b(chicken|beef|pork|lamb|mutton|turkey|duck|goose|rabbit|quail|veal|venison|bison|buffalo|goat)\b",
        re.IGNORECASE,
    )

    CARB_TUBER = re.compile(
        r"\b(potato|sweet potato|yam|cassava|taro|yuca|tapioca|jerusalem artichoke)\b",
        re.IGNORECASE,
    )
    CARB_GRAIN = re.compile(
        r"\b(rice|oat|oatmeal|wheat|corn|barley|sorghum|maize|millet|rye|buckwheat|quinoa|amaranth|teff|kamut|spelt|farro|pasta|macaroni|spaghetti|noodle|bread|flour|bran|germ|couscous|semolina|bulgur|biscuit|cracker)\b",
        re.IGNORECASE,
    )
    LEGUME = re.compile(
        r"\b(bean|pea|lentil|chickpea|soy|tofu|edamame)\b",
        re.IGNORECASE,
    )

    VEGETABLE = re.compile(
        r"\b(carrots?|broccoli|spinach|kale|cabbage|lettuce|celery|pepper|asparagus|zucchini|cucumber|pumpkin|squash|cauliflower|bean sprout|alfalfa|beet|turnip|parsnip|radish|mushroom|kelp|seaweed|algae|collard|green bean)\b",
        re.IGNORECASE,
    )
    FIBER = re.compile(r"\b(psyllium|flax|chia|hemp seed)\b", re.IGNORECASE)
    BERRY = re.compile(
        r"\b(blueberries?|cranberry|strawberry|raspberry|blackberry|acai|currant|mulberry|pomegranate|cherry)\b",
        re.IGNORECASE,
    )


class DiversityPatterns:
    RUMINANT = re.compile(
        r"\b(beef|cow|veal|calf|bison|buffalo|lamb|mutton|sheep|goat|venison|deer|elk|camel|moose)\b",
        re.IGNORECASE,
    )
    PORK = re.compile(r"\b(pork|pig|ham|bacon|swine|boar)\b", re.IGNORECASE)
    WATERFOWL = re.compile(r"\b(duck|goose|geese)\b", re.IGNORECASE)
    POULTRY = re.compile(
        r"\b(chicken|hen|rooster|broiler|fryer|turkey|quail|pheasant|guinea fowl|egg)\b",
        re.IGNORECASE,
    )
    SHELLFISH = re.compile(
        r"\b(shrimp|prawn|crab|lobster|crayfish|clam|mussel|oyster|scallop|squid|octopus|calamari|snail|whelk)\b",
        re.IGNORECASE,
    )
    FISH = re.compile(
        r"\b(fish|salmon|tuna|cod|sardine|mackerel|herring|trout|tilapia|pollock|haddock|anchovy|catfish|bass|snapper|halibut|sole|flounder)\b",
        re.IGNORECASE,
    )
    EXOTIC = re.compile(
        r"\b(rabbit|hare|kangaroo|wallaby|crocodile|alligator|emu|ostrich)\b",
        re.IGNORECASE,
    )
    EGG = re.compile(r"\b(egg|eggs|yolk|white)\b", re.IGNORECASE),
    BERRY = re.compile(r'\b(blueberry|cranberry|strawberry|raspberry|blackberry|mulberry|acai|currant)\b', re.IGNORECASE),
    LEAFY = re.compile(r'\b(spinach|kale|lettuce|chard|cabbage|bok choy|greens|arugula|collard|watercress|endive|romaine)\b', re.IGNORECASE)
    CRUCIFEROUS = re.compile(r'\b(broccoli|cauliflower|brussels sprout|kohlrabi|radish|turnip|rutabaga)\b', re.IGNORECASE)
    ORANGE = re.compile(r'\b(carrot|pumpkin|squash|sweet potato|yam|papaya|cantaloupe|apricot|mango|persimmon)\b', re.IGNORECASE)
    FRUIT = re.compile(r'\b(apple|pear|banana|watermelon|melon|peach|plum|nectarine|pineapple|coconut|fig|date|kiwi)\b', re.IGNORECASE)
    OTHER_VEG = re.compile(r'\b(zucchini|cucumber|celery|asparagus|green bean|string bean|snap pea|mushroom|eggplant|pepper|bell pepper|okra|tomatillo|tomato)\b', re.IGNORECASE)

_COOKED_PAT = re.compile(
    r"\b(cooked|boiled|steamed|roasted|baked|fried|broiled|grilled|braised|poached|stewed|drained)\b",
    re.IGNORECASE,
)

_RAW_PAT = re.compile(r"\b(raw)\b", re.IGNORECASE)

_SUPPLEMENT_PAT = re.compile(
    r"\b(calcium|carbonate|citrate|gluconate|lactate|phosphate|vitamin|mineral|taurine|choline|iodized salt|salt|fish oil|omega-3|probiotic|supplement)\b",
    re.IGNORECASE,
)
