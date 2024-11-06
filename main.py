import pygame
import random
import math
from collections import deque

# Pygame initialization
pygame.init()

# Screen size
WIDTH, HEIGHT = 960, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
BROWN = (165, 42, 42)

# Colony Parameters
INITIAL_COLONY_SIZE = 100
MAX_COLONY_SIZE = 500
COLONY_GROWTH_RATE = 0.1  # Rate at which new ants spawn when conditions are met
INITIAL_FOOD_STORAGE = 1000
FOOD_CONSUMPTION_RATE = 0.1  # Food consumed per ant per frame
CRITICAL_FOOD_LEVEL = 300  # Below this, switch to scavenging priority
OPTIMAL_FOOD_LEVEL = 800  # Above this, switch to building priority

# Ant Parameters
ANTHILL_POINT = (WIDTH // 2, HEIGHT // 2)
PHEROMONE_STRENGTH = 100
BASE_ANT_SPEED = 1
PHEROMONE_DETECTION_RANGE_SQUARED = 200 ** 2
FOOD_DETECTION_RANGE_SQUARED = 100 ** 2
FOOD_COLLECTION_RANGE_SQUARED = 10 ** 2
DIRECTION_TOLERANCE = .7
FOOD_SPAWN_AMOUNT_PER_CLICK = 50


# Building Parameters
BUILD_RANGE = 30  # Range around nest where building occurs
BUILD_EFFICIENCY = 0.2  # How quickly building progress increases
MAX_NEST_SIZE = 200  # Maximum radius of the nest

def sq_dist(point1, point2):
    """Calculate squared distance between two points to avoid unnecessary square roots."""
    return (point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2


class Colony:
    def __init__(self):
        self.food_storage = INITIAL_FOOD_STORAGE
        self.nest_size = 20  # Initial nest radius
        self.population = INITIAL_COLONY_SIZE
        self.building_progress = 0
        
    def update(self, ants):
        # Consume food based on population
        self.food_storage -= len(ants) * FOOD_CONSUMPTION_RATE
        
        # Cap food storage at 0
        self.food_storage = max(0, self.food_storage)
        
        # Update nest size based on building progress
        if self.building_progress >= 100 and self.nest_size < MAX_NEST_SIZE:
            self.nest_size += 1
            self.building_progress = 0
            
        # Potentially add new ants if conditions are met
        if (self.food_storage > OPTIMAL_FOOD_LEVEL and 
            len(ants) < MAX_COLONY_SIZE and 
            random.random() < COLONY_GROWTH_RATE):
            return Ant(ANTHILL_POINT[0], ANTHILL_POINT[1], self)
        return None
    
    def get_ant_speed(self):
        # Ants can travel further as colony grows
        speed_multiplier = 1 + (self.nest_size - 20) / 100
        return BASE_ANT_SPEED * speed_multiplier


class Manager:
    def __init__(self, item_type):
        self.repository = [[[] for _ in range(HEIGHT // 10)] for _ in range(WIDTH // 10)]
        self.item_type = item_type
    
    def add(self, item):
        grid_x = item.x // 10
        grid_y = item.y // 10
        self.repository[grid_x][grid_y].append(item)

    def remove(self, item):
        grid_x = item.x // 10
        grid_y = item.y // 10
        if item in self.repository[grid_x][grid_y]:
            self.repository[grid_x][grid_y].remove(item)

# Updated spawn_food to pass food_manager as a parameter
def spawn_food(food_manager, x, y, amount):
    for _ in range(amount):
        food = Food(x, y)
        food_manager.add(food)

class Food:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.amount = random.randint(5, 20)  # Example amount of food

    def draw(self, surface):
        pygame.draw.circle(surface, GREEN, (self.x, self.y), 5)

class Pheromone:
    def __init__(self, x, y, strength=PHEROMONE_STRENGTH):
        self.x = x
        self.y = y
        self.strength = strength

    def decay(self):
        self.strength -= 1  # Example decay
        if self.strength < 0:
            self.strength = 0

    def draw(self, surface):
        if self.strength > 0:
            pygame.draw.circle(surface, BLUE, (self.x, self.y), 3, 1)

class Ant:
    def __init__(self, x, y, colony):
        self.x = x
        self.y = y
        self.colony = colony
        self.speed = colony.get_ant_speed()
        self.role = 'builder' if random.random() < 0.3 else 'scavenger'
        self.building = False
        self.has_food = False
        self.target = None  # Target for movement, such as food or the nest

    def move(self, food_manager):
        # Update speed based on colony size
        self.speed = self.colony.get_ant_speed()
        
        # Check if role should change based on colony needs
        self.update_role()
        
        # Food detection for scavengers
        if self.role == 'scavenger' and not self.has_food:
            self.find_food(food_manager)
        
        # Movement logic for scavengers
        if self.has_food:
            # Return to anthill if carrying food
            self.move_toward(ANTHILL_POINT)
            if sq_dist((self.x, self.y), ANTHILL_POINT) < FOOD_COLLECTION_RANGE_SQUARED:
                self.colony.food_storage += 20  # Example amount per food return
                self.has_food = False
        else:
            # Move toward target food if detected
            if self.target:
                self.move_toward((self.target.x, self.target.y))
                if sq_dist((self.x, self.y), (self.target.x, self.target.y)) < FOOD_COLLECTION_RANGE_SQUARED:
                    self.has_food = True
                    food_manager.remove(self.target)
                    self.target = None
            else:
                # Random movement if no food found
                self.x += random.choice([-1, 0, 1]) * self.speed
                self.y += random.choice([-1, 0, 1]) * self.speed

        # Builders occasionally build near the nest
        if self.role == 'builder' and not self.has_food:
            if random.random() < 0.3:
                self.building = True
                self.build()
                return
        self.building = False

    def move_toward(self, target_point):
        """Move towards a specific point."""
        dx, dy = target_point[0] - self.x, target_point[1] - self.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist != 0:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    def find_food(self, food_manager):
        """Look for food within detection range."""
        for row in food_manager.repository:
            for tile in row:
                for food in tile:
                    if sq_dist((self.x, self.y), (food.x, food.y)) < FOOD_DETECTION_RANGE_SQUARED:
                        self.target = food
                        return

    def update_role(self):
        if self.colony.food_storage < CRITICAL_FOOD_LEVEL:
            # Emergency - everyone becomes a scavenger
            self.role = 'scavenger'
        elif self.colony.food_storage > OPTIMAL_FOOD_LEVEL:
            # Plenty of food - maintain builder ratio
            if random.random() < 0.1:  # Small chance to switch roles
                self.role = 'builder' if random.random() < 0.3 else 'scavenger'
                
    def build(self):
        if sq_dist((self.x, self.y), ANTHILL_POINT) < BUILD_RANGE ** 2:
            self.colony.building_progress += BUILD_EFFICIENCY
            
    def draw(self, surface):
        color = GREEN if self.has_food else (BROWN if self.role == 'builder' else WHITE)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), 3)



# Modified main game loop
def main():
    clock = pygame.time.Clock()
    food_manager = Manager(Food)
    pheromone_manager = Manager(Pheromone)
    
    # Initialize colony
    colony = Colony()
    ants = [Ant(ANTHILL_POINT[0], ANTHILL_POINT[1], colony) for _ in range(INITIAL_COLONY_SIZE)]
    
    # Spawning initial food
    spawn_food(food_manager, 480, 150, FOOD_SPAWN_AMOUNT_PER_CLICK * 3)
    spawn_food(food_manager, 480, 930, FOOD_SPAWN_AMOUNT_PER_CLICK * 3)
    
    # Main Loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                (x, y) = pygame.mouse.get_pos()
                spawn_food(food_manager, x, y, FOOD_SPAWN_AMOUNT_PER_CLICK)
                
        screen.fill(BLACK)
        
        # Update colony and potentially add new ants
        new_ant = colony.update(ants)
        if new_ant:
            ants.append(new_ant)
            
        # Draw nest with size based on colony growth
        pygame.draw.circle(screen, YELLOW, ANTHILL_POINT, radius=colony.nest_size)
        
        # Draw food storage indicator
        food_height = (colony.food_storage / INITIAL_FOOD_STORAGE) * 100
        pygame.draw.rect(screen, GREEN, (10, HEIGHT - food_height - 10, 20, food_height))
        
        # Draw building progress
        build_height = (colony.building_progress / 100) * 50
        pygame.draw.rect(screen, BROWN, (40, HEIGHT - build_height - 10, 20, build_height))
        
        # Update and draw pheromones
        for row in pheromone_manager.repository:
            for tile in row:
                for pheromone in tile.copy():
                    pheromone.decay()
                    if pheromone.strength == 0:
                        pheromone_manager.remove(pheromone)
                    else:
                        pheromone.draw(screen)
        
        # Move and draw ants
        for ant in ants:
            ant.move(food_manager)
            ant.draw(screen)

        
        # Draw food
        for row in food_manager.repository:
            for tile in row:
                for food in tile:
                    food.draw(screen)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()
