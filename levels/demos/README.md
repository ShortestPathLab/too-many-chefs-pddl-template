# Demo kitchens

Self-contained examples of recipes, layouts, and simulator rules. Run from the
repository root, for example:

```sh
uv run cook play --level levels/demos/coconut_juice.yaml
```

Start with coconut juice, then try fruit salad, burgers, sushi, chicken and
chips, and finally black forest cake. Each YAML includes its layout, orders,
legend, recipes, appearance, and soundtrack; catalog defaults supply the food
and equipment definitions.

## Recipes

| Level | Chefs | What it demonstrates |
| --- | --- | --- |
| [coconut_juice.yaml](coconut_juice.yaml) | 1 | Retrieve, chop, plate, and deliver a single ingredient. |
| [fruit_salad.yaml](fruit_salad.yaml) | 1 | Chop two fruits, combine a salad, then add yoghurt for a parfait. |
| [burger.yaml](burger.yaml) | 1 | Grill in a pan on a stove, slice cheese, and assemble hamburgers and cheeseburgers in different orders. |
| [sushi.yaml](sushi.yaml) | 1 | Boil rice in a pot; chop or grill fish for sushi and fish-and-rice bowls. |
| [chicken_and_chips.yaml](chicken_and_chips.yaml) | 1 | Bake chicken, chop and deep-fry potatoes, then combine the finished dish. |
| [black_forest_cake.yaml](black_forest_cake.yaml) | 1 | Assemble batter ingredients, use a mixing bowl and mixer, bake, and add toppings. |

## Rules and starting state

| Level | Chefs | What it demonstrates |
| --- | --- | --- |
| [coconut_juice_prepared.yaml](coconut_juice_prepared.yaml) | 1 | Three orders supplied by a prepared juice, two loose raw coconuts, with no replenishing storage. |
| [burger_strict_order.yaml](burger_strict_order.yaml) | 1 | All orders visible; deliveries must follow queue order. |
| [burger_sequential.yaml](burger_sequential.yaml) | 2 | Reveal one order at a time in a divided kitchen; reward useful recipe progress. |
| [burger_sequential_timed.yaml](burger_sequential_timed.yaml) | 2 | Sequential tickets with default and per-order deadlines and rewards. |
| [burger_infinite.yaml](burger_infinite.yaml) | 1 | Seeded replacement orders, two visible tickets, and a plate dispenser. |
| [burger_washing_up.yaml](burger_washing_up.yaml) | 1 | Infinite orders with one reusable plate, dirty returns, and a sink. |
| [burger_anything_goes.yaml](burger_anything_goes.yaml) | 1 | Illegal cooking and combinations produce failed food; use the bin to recover. |
| [burger_timed.yaml](burger_timed.yaml) | 1 | Timed cooking: the pan grills by itself while the cutboard needs several chops, so the chef slices cheese while the patty cooks. |

Infinite-order demos need `--time-limit` for headless agent runs. Timed orders
can expire; these examples demonstrate the rule rather than guarantee that
every controller will complete every ticket.

## Layout and team variants

| Levels | What it demonstrates |
| --- | --- |
| [coconut_juice_tiny.yaml](coconut_juice_tiny.yaml), [coconut_juice_tiny_2p.yaml](coconut_juice_tiny_2p.yaml) | Compact layouts with one or two chefs. |
| [fruit_salad_2p.yaml](fruit_salad_2p.yaml), [burger_2p.yaml](burger_2p.yaml) | Two chefs sharing a recipe's preparation work. |
| [burger_large.yaml](burger_large.yaml) | Longer travel distances in a larger solo kitchen. |
| [chicken_and_chips_2p.yaml](chicken_and_chips_2p.yaml), [chicken_and_chips_4p.yaml](chicken_and_chips_4p.yaml), [chicken_and_chips_8p.yaml](chicken_and_chips_8p.yaml) | Shared kitchens with increasing numbers of chefs. |
| [chicken_and_chips_2p_divided.yaml](chicken_and_chips_2p_divided.yaml) | Separate work areas requiring counter handoffs. |

The graded practice sequences remain in [I can cook](../0_i_can_cook/README.md),
[We can cook](../1_we_can_cook/README.md), and [Overcooked](../2_overcooked/README.md).
