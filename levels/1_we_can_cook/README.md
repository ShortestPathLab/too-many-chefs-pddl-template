# We Can Cook

Cooperative levels. Every level has at least two chefs and two orders, and
every order has a time limit. The first number in a file name is the recipe,
and the second ranks that recipe's kitchens from easiest to hardest.

- `0_*_burger_*`: basic cooperative assembly and grilling
- `1_*_sushi_*`: parallel preparation paths for sushi and fish-and-rice bowls
- `2_*_chicken_and_chips_*`: independent cooking chains joined at assembly

The kitchens use these layouts:

- `parallel_stations`: two complete work areas
- `shared_stations`: shared equipment creates a bottleneck
- `divided`: chefs work on opposite sides of a pass counter
- `divided_storages_one_side`: all ingredient storage is on one side
- `divided_pass_through`: stations and ingredients are balanced, but ingredients
  start opposite the station that processes them
- `four_divided`: four chefs occupy separate quadrants and exchange food across
  pass counters
