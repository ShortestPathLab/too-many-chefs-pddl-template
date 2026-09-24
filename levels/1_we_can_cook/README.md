# We Can Cook

Cooperative levels. Every level has at least two chefs and two orders.

- `0_burger_*`: basic cooperative assembly and grilling
- `1_sushi_*`: parallel preparation paths for sushi and fish-and-rice bowls
- `2_chicken_and_chips_*`: independent cooking chains joined at assembly

Each recipe progresses through:

- `parallel_stations`: two complete work areas
- `shared_stations`: shared equipment creates a bottleneck
- `divided`: chefs work on opposite sides of a pass counter
- `divided_storages_one_side`: all ingredient storage is on one side
- `divided_pass_through`: stations and ingredients are balanced, but ingredients
  start opposite the station that processes them
- `four_divided`: four chefs occupy separate quadrants and exchange food across
  pass counters
