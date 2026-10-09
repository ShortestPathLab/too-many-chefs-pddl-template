# I Can Cook

Solo levels that introduce cooking in three steps. The first number in a file
name is the recipe, and the second ranks that recipe's levels from easiest to
hardest, so the files sort in the order to try them.

- `0_*_coconut_juice_*`: one ingredient and one transformation
- `1_*_fruit_parfait_*`: multiple ingredients and one or more remaining transformations
- `2_*_cheeseburger_*`: assembly from processed, partially processed, or raw ingredients

Every order has a time limit, given as `time_limit` in the level file.

Ingredient dispensers are called `storages` in the level schema. Schema `bins` are
trash bins, so level names use `storage` where the teaching notes say "bin".
