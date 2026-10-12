// Layer 2: ordinary DOM pinned to a world position.
//
// Two modes. Given a trackId it follows that renderable's *interpolated*
// position, so a badge slides across a cell in step with the sprite it labels
// instead of teleporting when the simulation ticks. Without one it sits at a
// fixed grid coordinate.

export default {
  template: /*html*/ `
    <div class="world-anchor" style="position: absolute; will-change: transform;">
      <slot></slot>
    </div>
  `,
  props: {
    cameraId: { type: String, default: "world" },
    // Renderable to follow. Empty means use gridX/gridY directly.
    trackId: { type: String, default: "" },
    gridX: { type: Number, default: 0 },
    gridY: { type: Number, default: 0 },
    // Added to the tracked position, in cells, so offsets survive zoom changes.
    offsetCellsX: { type: Number, default: 0 },
    offsetCellsY: { type: Number, default: 0 },
    // Fraction of the anchor's own size to pull back by: (0.5, 1) hangs it
    // above a point, (0.5, 0.5) centres it.
    originX: { type: Number, default: 0.5 },
    originY: { type: Number, default: 1 },
    offsetX: { type: Number, default: 0 },
    offsetY: { type: Number, default: 0 },
  },
  data() {
    return { camera: null, unsubscribers: [] };
  },
  mounted() {
    const api = window.tooManyChefsCamera;
    if (api) {
      this.unsubscribers.push(
        api.subscribeCamera(this.cameraId, (camera) => {
          this.camera = camera;
          this.place();
        }),
      );
      if (this.trackId) {
        this.unsubscribers.push(
          api.subscribeTracks(this.cameraId, () => this.place()),
        );
      }
    }
    this.place();
  },
  beforeUnmount() {
    for (const unsubscribe of this.unsubscribers) {
      unsubscribe?.();
    }
  },
  watch: {
    gridX() {
      this.place();
    },
    gridY() {
      this.place();
    },
  },
  methods: {
    basePosition() {
      if (!this.trackId) {
        return { x: this.gridX, y: this.gridY };
      }
      const track = window.tooManyChefsCamera?.getTrack(
        this.cameraId,
        this.trackId,
      );
      // Before the first draw, or for a renderable that has left the scene,
      // fall back to whatever Python last said.
      if (!track) {
        return { x: this.gridX, y: this.gridY };
      }
      return { x: track.x + this.offsetCellsX, y: track.y + this.offsetCellsY };
    },
    place() {
      if (!this.camera) {
        // Nothing to anchor to yet. Stay hidden rather than flash at 0,0.
        this.$el.style.visibility = "hidden";
        return;
      }
      const { unit, scale, originX, originY } = this.camera;
      const base = this.basePosition();
      const left = (originX + base.x * unit) * scale + this.offsetX;
      const top = (originY + base.y * unit) * scale + this.offsetY;
      this.$el.style.visibility = "visible";
      this.$el.style.left = `${left}px`;
      this.$el.style.top = `${top}px`;
      this.$el.style.transform =
        `translate(${-this.originX * 100}%, ${-this.originY * 100}%)`;
    },
  },
};
