; PDDL domain for the starter example. The domain defines object types,
; predicates and actions shared across kitchens. problem_generator.py
; generates a problem describing a particular kitchen's objects, initial
; facts and goals. from_pddl.py translates the planned actions into simulator
; mutations.
;
; This template supports collecting a plate, placing prepared food on it and
; delivering it. Extend the types, predicates and actions to support
; other levels.
;
; The domain does not model movement. The controller positions the chef
; before each action, so actions do not specify the chef's position.
;
; All preconditions are positive, because pyperplan, one of the bundled
; solvers, rejects (not ...) in preconditions. Negated effects are supported.
; To express a negative condition, define a positive predicate for it:
; hand_empty is true exactly when the chef is holding nothing.
(define (domain overcooked)
  ; :strips allows actions that add and delete facts, and :typing allows the
  ; types below. Declare any further PDDL feature the domain uses here.
  (:requirements :strips :typing)

  ; An item is an object the chef can carry. Each food type has one object,
  ; as does each plate state: empty_plate or a plate containing a given food.
  ; food and plate are both kinds of item, so a parameter of type item
  ; accepts either. location and item are direct subtypes of object, the
  ; root of the type hierarchy.
  (:types
    location item - object
    food plate - item
  )

  (:predicates
    ; The chef is holding nothing.
    (hand_empty)
    ; The chef is holding ?item.
    (holding ?item - item)
    ; ?item is on the counter at ?location.
    (item_at ?item - item ?location - location)
    ; Dishes are served at ?location.
    (delivery_location ?location - location)
    ; Adding ?food to ?plate produces the plate state ?result.
    (plating ?plate - plate ?food - food ?result - plate)
    ; ?plate, a plate containing a dish, has been served; used in delivery goals.
    (delivered ?plate - plate)
  )

  ; Each action has :parameters, which the planner binds to objects from
  ; the problem, a :precondition that must hold before the action, and an
  ; :effect that adds facts and removes those negated with (not ...).
  ; from_pddl.py reads each step's arguments in the order of :parameters, so
  ; if you add or reorder parameters, update from_pddl.py to match.

  ; The chef picks up ?item from the counter at ?location.
  (:action pick_up
    :parameters (?item - item ?location - location)
    :precondition (and
      (hand_empty)
      (item_at ?item ?location)
    )
    :effect (and
      (holding ?item)
      (not (hand_empty))
      (not (item_at ?item ?location))
    )
  )

  ; The chef adds the food at ?location to the plate it is holding. The
  ; plating fact identifies ?result, the object representing the new plate
  ; state, which replaces the held plate in the model.
  (:action add_to_plate
    :parameters (?plate - plate ?food - food ?location - location ?result - plate)
    :precondition (and
      (holding ?plate)
      (item_at ?food ?location)
      (plating ?plate ?food ?result)
    )
    :effect (and
      (holding ?result)
      (not (holding ?plate))
      (not (item_at ?food ?location))
    )
  )

  ; The chef serves the plate it is holding at a delivery tile and is left
  ; empty-handed.
  (:action deliver
    :parameters (?plate - plate ?location - location)
    :precondition (and
      (holding ?plate)
      (delivery_location ?location)
    )
    :effect (and
      (delivered ?plate)
      (hand_empty)
      (not (holding ?plate))
    )
  )
)
