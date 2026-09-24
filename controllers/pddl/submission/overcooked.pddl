; Your kitchen domain. This starting point knows nothing about the kitchen
; beyond chefs and the four directions they can face; see
; problem_generator.py for the problem that goes with it.
;
; Preconditions here are positive only, which every bundled solver accepts.
(define (domain kitchen-demo)
  (:requirements :strips :typing)

  (:types chef direction)

  (:predicates
    (facing ?c - chef ?d - direction)
  )

  (:action turn
    :parameters (?c - chef ?from - direction ?to - direction)
    :precondition (facing ?c ?from)
    :effect (and
      (not (facing ?c ?from))
      (facing ?c ?to)
    )
  )
)
