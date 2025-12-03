import random

class NLPTranslator:
    def __init__(self):
        self.mappings = {
            "Dog": {
                "Happy": ["I love you, human!", "Play with me!", "This is the best day ever!"],
                "Angry": ["Back off!", "I'm warning you!", "Grrr, go away!"],
                "Sad": ["I miss you.", "Where did you go?", "I'm lonely."],
                "Hungry": ["Feed me!", "Is that bacon?", "I'm starving here!"],
                "Pain": ["Ouch, that hurts.", "Help me, please.", "I'm not feeling well."]
            },
            "Cat": {
                "Happy": ["Purr... perfect.", "You may pet me now.", "I tolerate you."],
                "Angry": ["Hiss! Don't touch me!", "I will scratch you.", "Leave me be."],
                "Sad": ["My bowl is empty.", "Why is the door closed?", "Sigh."],
                "Hungry": ["Feed me now, servant.", "Meow! Food!", "I can see the bottom of my bowl."],
                "Pain": ["Hiss... stay away.", "It hurts.", "Don't touch."]
            },
            # Add more animals as needed
        }
        self.default_responses = ["I don't know what to say.", "Hello there.", "What was that?"]

    def translate(self, animal, emotion):
        """
        Translate animal + emotion to a natural language sentence.
        """
        try:
            options = self.mappings.get(animal, {}).get(emotion, self.default_responses)
            return random.choice(options)
        except:
            return "I am an animal."

translator = NLPTranslator()
