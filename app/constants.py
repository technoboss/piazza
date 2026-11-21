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


# The only two reactions a user can give. A str enum, so
# Pydantic rejects anything else (for example "love") with a 422.
class ReactionType(str, Enum):
    like = "like"
    dislike = "dislike"


# The two states a post can be in is "Live" and "Expired". used by the ?status= filter. 
class PostStatus(str, Enum):
    live = "Live"
    expired = "Expired"