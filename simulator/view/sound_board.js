// Sound effects for the simulator.
//
// Web Audio rather than <audio> elements: clips are short, several can land on
// the same step, and an AudioContext gives overlapping playback plus per-cue
// gain without a pool of elements to manage.
//
// Browsers refuse to start an AudioContext until the page has been interacted
// with. Every run mode is keyboard driven, so the first keypress unlocks it;
// until then cues are dropped rather than queued, because a burst of stale
// sounds on unlock is worse than silence.

const BUFFERS = new Map(); // url -> AudioBuffer
const PENDING = new Map(); // url -> Promise<AudioBuffer|null>
const LAST_PICK = new Map(); // cue name -> index played last time

let context = null;

// Pick a take at random, but never the one that just played. Repeating a
// sample back to back is what makes a footstep sound synthetic, and it is
// exactly what an unguarded Math.random does a fifth of the time.
function pickVariant(name, urls) {
  if (urls.length === 1) {
    return urls[0];
  }
  const previous = LAST_PICK.get(name);
  let index = Math.floor(Math.random() * urls.length);
  if (index === previous) {
    index = (index + 1 + Math.floor(Math.random() * (urls.length - 1))) % urls.length;
  }
  LAST_PICK.set(name, index);
  return urls[index];
}

// Where each copy of a multi-sample cue lands, in seconds from now.
//
// The window is cut into one slot per copy and each copy lands somewhere inside
// its own slot. Straight uniform randomness would let two footfalls come within
// a millisecond of each other, which is heard as one flammed step rather than
// as a stride; slotting guarantees they stay apart while still landing
// unevenly. A lone copy plays immediately, since there is nothing to separate
// it from and a delay would just be latency.
function scatter(count, spread) {
  if (count < 2 || spread <= 0) {
    return new Array(count).fill(0);
  }
  return Array.from(
    { length: count },
    (_, index) => ((index + Math.random()) / count) * spread,
  );
}

function audioContext() {
  if (context === null) {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    context = Ctor ? new Ctor() : undefined;
  }
  return context || null;
}

async function loadClip(url) {
  if (BUFFERS.has(url)) {
    return BUFFERS.get(url);
  }
  if (PENDING.has(url)) {
    return PENDING.get(url);
  }
  const ctx = audioContext();
  if (!ctx) {
    return null;
  }
  const pending = fetch(url)
    .then((response) => response.arrayBuffer())
    .then((bytes) => ctx.decodeAudioData(bytes))
    .then((buffer) => {
      BUFFERS.set(url, buffer);
      return buffer;
    })
    .catch(() => null);
  PENDING.set(url, pending);
  return pending;
}

export default {
  template: `<div class="sound-board" style="display: none;"></div>`,
  props: {
    // Cue name -> list of interchangeable clip urls, plus cue name -> gain and
    // cue name -> pitch jitter.
    sounds: { type: Object, default: () => ({}) },
    gains: { type: Object, default: () => ({}) },
    jitters: { type: Object, default: () => ({}) },
    // Cue name -> how many samples one event of that cue is worth, and how many
    // seconds wide the window is that those copies are thrown across.
    repeats: { type: Object, default: () => ({}) },
    spreads: { type: Object, default: () => ({}) },
    volume: { type: Number, default: 1 },
    muted: { type: Boolean, default: false },
  },
  data() {
    return { unlocked: false, master: null };
  },
  mounted() {
    for (const type of ["keydown", "pointerdown"]) {
      window.addEventListener(type, this.unlock, { passive: true });
    }
    this.preload();
  },
  beforeUnmount() {
    for (const type of ["keydown", "pointerdown"]) {
      window.removeEventListener(type, this.unlock);
    }
  },
  watch: {
    sounds: {
      deep: true,
      handler() {
        this.preload();
      },
    },
  },
  methods: {
    preload() {
      for (const urls of Object.values(this.sounds ?? {})) {
        for (const url of urls) {
          loadClip(url);
        }
      }
    },

    unlock() {
      const ctx = audioContext();
      if (!ctx) {
        return;
      }
      if (ctx.state === "suspended") {
        ctx.resume();
      }
      this.unlocked = true;
    },

    // Called from Python as run_method('play', name).
    async play(name, delay = 0) {
      if (this.muted) {
        return;
      }
      const urls = this.sounds?.[name];
      if (!urls || urls.length === 0) {
        return;
      }
      const ctx = audioContext();
      if (!ctx || ctx.state !== "running") {
        return;
      }
      // Fixed before the await, so a clip that has to be fetched and decoded
      // arrives late rather than landing a whole decode after its neighbours.
      const when = ctx.currentTime + delay;
      const buffer = await loadClip(pickVariant(name, urls));
      if (!buffer) {
        return;
      }

      if (!this.master) {
        this.master = ctx.createGain();
        this.master.connect(ctx.destination);
      }
      this.master.gain.value = this.volume;

      const gain = ctx.createGain();
      gain.gain.value = this.gains?.[name] ?? 1;
      gain.connect(this.master);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      const jitter = this.jitters?.[name] ?? 0;
      if (jitter > 0) {
        source.playbackRate.value = 1 + (Math.random() * 2 - 1) * jitter;
      }
      source.connect(gain);
      // Scheduling rather than sleeping: the clock the sound is placed against
      // is the audio clock, so a slot two milliseconds wide survives a busy
      // main thread that a setTimeout would not.
      source.start(when);
      source.onended = () => {
        source.disconnect();
        gain.disconnect();
      };
    },

    // Called from Python as run_method('playAll', names).
    //
    // Occurrences of a name are counted before anything is scheduled, so all of
    // a cue's copies are thrown across one window rather than each starting a
    // window of its own. The caller sends a deduplicated list today, and this
    // stays right if it ever stops.
    async playAll(names) {
      const counts = new Map();
      for (const name of names ?? []) {
        counts.set(name, (counts.get(name) ?? 0) + 1);
      }
      for (const [name, count] of counts) {
        const copies = count * Math.max(1, this.repeats?.[name] ?? 1);
        for (const delay of scatter(copies, this.spreads?.[name] ?? 0)) {
          this.play(name, delay);
        }
      }
    },
  },
};
