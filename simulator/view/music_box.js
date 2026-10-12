// The level's soundtrack.
//
// An <audio> element rather than the Web Audio graph the cues run through: a
// track is minutes of mp3, so it wants streaming. Fetching and decoding the
// whole file the way a sample is decoded would hold the music back until long
// after the first order.
//
// Browsers refuse to start audio until the page has been interacted with, and
// the first keypress of a run is what unlocks it. Nothing drives this from
// Python: the element reports each track ending and the next one is started
// here, so a two-track level scores a run of any length.

export default {
  template: `<audio class="music-box" preload="auto" style="display: none;"></audio>`,
  props: {
    // Track urls, in the order the level wants them played.
    tracks: { type: Array, default: () => [] },
    // How loud the music sits under the kitchen, and the master volume the whole
    // app is running at. The two are multiplied, so muting or turning the app
    // down takes the music with it.
    gain: { type: Number, default: 0.2 },
    volume: { type: Number, default: 1 },
    muted: { type: Boolean, default: false },
  },
  data() {
    return { index: 0 };
  },
  mounted() {
    for (const type of ["keydown", "pointerdown"]) {
      window.addEventListener(type, this.start, { passive: true });
    }
    this.$el.addEventListener("ended", this.advance);
    this.load(0);
    // Worth one try: a page the browser already trusts starts the music without
    // waiting for a keypress, and one that does not refuses quietly.
    this.start();
  },
  beforeUnmount() {
    for (const type of ["keydown", "pointerdown"]) {
      window.removeEventListener(type, this.start);
    }
    this.$el.removeEventListener("ended", this.advance);
    this.$el.pause();
  },
  watch: {
    tracks: {
      deep: true,
      handler() {
        this.load(0);
        this.start();
      },
    },
    gain() {
      this.applyVolume();
    },
    volume() {
      this.applyVolume();
    },
    muted() {
      this.applyVolume();
    },
  },
  methods: {
    applyVolume() {
      // Clamped because the element throws on anything outside 0 to 1, and it is
      // fed two numbers that were each set somewhere else.
      this.$el.volume = Math.min(1, Math.max(0, this.gain * this.volume));
      // Muted rather than paused, so the track keeps its place and the music
      // comes back where it would have been rather than where it left off.
      this.$el.muted = this.muted;
    },

    load(index) {
      const tracks = this.tracks ?? [];
      if (tracks.length === 0) {
        return;
      }
      this.index = index % tracks.length;
      // A single-track playlist loops in the element rather than here: assigning
      // the same url again refetches it and leaves a hole where the loop should
      // be.
      this.$el.loop = tracks.length === 1;
      this.$el.src = tracks[this.index];
      this.applyVolume();
    },

    advance() {
      this.load(this.index + 1);
      this.start();
    },

    start() {
      if (!this.$el.src) {
        return;
      }
      // Rejected for as long as the page is untrusted, which is every moment
      // before the first keypress. The listener tries again on each one.
      const started = this.$el.play();
      if (started && started.catch) {
        started.catch(() => {});
      }
    },
  },
};
