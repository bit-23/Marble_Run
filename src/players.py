class players:
    def __init__(self, name, score):
        self.name = name
        self.score = score

    def update_score(self, points):
        self.score += points

    def __str__(self):
        return f"{self.name}: {self.score}"
    
def create_player(name):
    return players(name, 0)