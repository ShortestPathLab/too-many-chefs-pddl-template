# Overcooked

Challenge levels with long recipes, multiple handoffs, and up to four chefs.
Every order has a time limit. The first number in a file name is the group
below, and the second ranks the group's levels from easiest to hardest.

Black forest cake in the layouts from We Can Cook:

- `0_0_black_forest_cake_shared_stations_2p`: two chefs share every
  preparation stage
- `0_1_black_forest_cake_parallel_stations_4p`: four chefs have room to process
  several cakes at once
- `0_2_black_forest_cake_divided_3p`: ingredients and equipment are split
  across a pass counter
- `0_3_black_forest_cake_four_divided_4p`: batter, chocolate, baking, and
  decorating occupy separate quadrants

The rest of the pack turns on the kitchen's other rules, one idea per level.

Plates:

- `1_0_cheeseburger_dish_pit_2p`: one plate that comes back dirty, with the sink
  and the dispenser at opposite ends
- `1_1_black_forest_cake_mid_service_2p`: a cake in the oven, half-mixed batter,
  chefs already holding ingredients, and only one clean plate

Time (`timed_cooking`):

- `2_0_black_forest_cake_slow_oven_2p`: a 12-step oven is the bottleneck for
  three cakes
- `2_1_burger_burning_2p`: grilled meat left in the pan burns four steps later

Order rules:

- `3_0_sushi_rush_hour_3p`: tickets revealed one at a time with deadlines, and a
  high-value ticket on a short clock
- `3_1_serve_in_order_2p`: strict ordering with one plate and one cutboard, so
  preparing the quick juice first can deadlock the kitchen

Robustness:

- `4_0_black_forest_cake_out_of_stock_2p`: two loose cherries for three cakes and
  no meat at all, so not every order can be filled
- `4_1_black_forest_cake_wrong_room_3p`: the mixing bowl starts on the wrong side
  of the pass, the cutboard starts with dubious food on it, and illegal recipes
  are on
