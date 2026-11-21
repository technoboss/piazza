# The four fixed topics. One place defines them, so the database,
# the validation and the API always agree on the exact names.
from enum import Enum


class TopicName(str, Enum):
    politics = "Politics"
    health = "Health"
    sport = "Sport"
    tech = "Tech"


TOPIC_DESCRIPTIONS = {
    TopicName.politics: "Government, policy and elections",
    TopicName.health: "Medicine, wellbeing and public health",
    TopicName.sport: "Competitions, teams and athletes",
    TopicName.tech: "Software, hardware and the internet",
}