import random

from app.models.content import ContentLanguage, ContentType

TALES = [
    "The tortoise and the hare race to the finish line with unexpected results.",
    "Goldilocks discovers three bears' houses and learns to respect others' property.",
    "The three little pigs build houses of different materials and learn the importance of hard work and perseverance.",
    "Cinderella overcomes her hardships and wins the heart of the prince with the help of her fairy godmother.",
    "The ugly duckling is ridiculed for its appearance, but eventually transforms into a beautiful swan.",
    "The little fairy found her lost wand in the field of flowers.",
    "The prince rescued the cursed princess with a true love's kiss.",
    "The mischievous gnome tricked the farmer into planting magic beans.",
    "The mermaid fell in love with a human and traded her tail for legs.",
    "The brave knight defeated the fire-breathing dragon and saved the kingdom.",
    "The clever fox outwitted the greedy wolf and kept the golden treasure.",
    "The enchanted forest came alive at midnight and danced until dawn.",
    "The talking animals helped the lost child find her way home.",
    "The kind sorceress turned the wicked witch into a harmless toad.",
    "The friendly giant shared his magical beans with the poor village.",
]
FACTS = [
    "Did you know that a group of flamingos is called a flamboyance?",
    "The shortest war in history lasted only 38 minutes between Britain and Zanzibar in 1896.",
    "Elephants are the only mammals that can't jump.",
    "The Great Barrier Reef is the world's largest living structure, visible even from outer space.",
    "The tallest waterfall in the world is Angel Falls in Venezuela, measuring over 3,200 feet (979 meters) high.",
    "Did you know that cats can make over 100 different sounds but dogs can only make about 10?",
    "Did you know that a group of flamingos is called a flamboyance?",
    "Did you know that the shortest war in history was between Britain and Zanzibar and lasted only 38 minutes?",
    "Did you know that the word 'nerd' was first coined by Dr. Seuss in 'If I Ran the Zoo'?",
    "Did you know that a sneeze can travel up to 100 miles per hour?",
    "Did you know that the longest word in the English language has 189,819 letters and takes over three hours to pronounce?",
    "Did you know that there is a species of jellyfish that is immortal and can live forever?",
    "Did you know that a small child could swim through the veins of a blue whale?",
    "Did you know that the world's largest snowflake on record was 15 inches wide and 8 inches thick?",
    "Did you know that a group of pugs is called a grumble?",
]

TypeToContentMap = {
    ContentType.TALE: TALES,
    ContentType.FACTS: FACTS,
}


def generate_content(content_type: ContentType, lang: ContentLanguage = ContentLanguage.ENGLISH):
    return random.choice(TypeToContentMap[content_type])
