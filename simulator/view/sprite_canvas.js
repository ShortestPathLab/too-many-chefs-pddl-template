// A canvas that draws a list of renderables and nothing else.
//
// It knows about sprite sheets, source rectangles, a transform, and frame
// animation. It does not know what an Agent is, what an order is, or where the
// HUD goes. Every instance shares the caches below, because NiceGUI registers a
// component module once per class and instantiates it per element.

const SHEET_IMAGES = new Map(); // url -> HTMLImageElement
const SHEET_LOADS = new Map(); // url -> Promise<void>

const TICKS_PER_SECOND = 8;

function loadSheet(url) {
  if (SHEET_LOADS.has(url)) {
    return SHEET_LOADS.get(url);
  }
  const pending = new Promise((resolve) => {
    const attempt = (retriesLeft) => {
      const image = new Image();
      image.onload = () => {
        SHEET_IMAGES.set(url, image);
        resolve();
      };
      image.onerror = () => {
        if (retriesLeft > 0) {
          setTimeout(() => attempt(retriesLeft - 1), 500);
        } else {
          // A later component may try again; never cache a failed download.
          SHEET_LOADS.delete(url);
          console.warn(`Could not load sprite sheet: ${url}`);
          resolve();
        }
      };
      image.src = url;
    };
    attempt(2);
  });
  SHEET_LOADS.set(url, pending);
  return pending;
}

// Camera registry. Layer 2 (DOM positioned in world coordinates) needs the same
// scale and origin the world canvas settled on. Publishing it here keeps that
// lookup inside the browser instead of round-tripping through Python. Exposed on
// window as well so sibling components can read it without resolving a relative
// module path against NiceGUI's component URLs.
const CAMERAS = new Map();
const CAMERA_SUBSCRIBERS = new Map();

export function getCamera(cameraId) {
  return CAMERAS.get(cameraId) ?? null;
}

export function subscribeCamera(cameraId, callback) {
  if (!CAMERA_SUBSCRIBERS.has(cameraId)) {
    CAMERA_SUBSCRIBERS.set(cameraId, new Set());
  }
  CAMERA_SUBSCRIBERS.get(cameraId).add(callback);
  const current = CAMERAS.get(cameraId);
  if (current) {
    callback(current);
  }
  return () => CAMERA_SUBSCRIBERS.get(cameraId)?.delete(callback);
}

export function worldToScreen(cameraId, gridX, gridY) {
  const camera = CAMERAS.get(cameraId);
  if (!camera) {
    return null;
  }
  return {
    x: (camera.originX + gridX * camera.unit) * camera.scale,
    y: (camera.originY + gridY * camera.unit) * camera.scale,
  };
}

// Interpolated positions, republished every time the world redraws.
//
// A renderable mid-transition is not where the simulation says it is: the canvas
// walks it across the cell over the frames of its init animation. Anything
// pinned to a moving entity has to read the same interpolated value, or it
// arrives a whole cell early and jumps.
const TRACKS = new Map(); // cameraId -> Map<renderableId, {x, y}>
const TRACK_SUBSCRIBERS = new Map(); // cameraId -> Set<callback>

export function getTrack(cameraId, renderableId) {
  return TRACKS.get(cameraId)?.get(renderableId) ?? null;
}

export function subscribeTracks(cameraId, callback) {
  if (!TRACK_SUBSCRIBERS.has(cameraId)) {
    TRACK_SUBSCRIBERS.set(cameraId, new Set());
  }
  TRACK_SUBSCRIBERS.get(cameraId).add(callback);
  callback();
  return () => TRACK_SUBSCRIBERS.get(cameraId)?.delete(callback);
}

function publishTracks(cameraId, positions) {
  TRACKS.set(cameraId, positions);
  for (const callback of TRACK_SUBSCRIBERS.get(cameraId) ?? []) {
    callback();
  }
}

function publishCamera(cameraId, camera) {
  const previous = CAMERAS.get(cameraId);
  if (
    previous &&
    previous.scale === camera.scale &&
    previous.originX === camera.originX &&
    previous.originY === camera.originY &&
    previous.unit === camera.unit
  ) {
    return;
  }
  CAMERAS.set(cameraId, camera);
  for (const callback of CAMERA_SUBSCRIBERS.get(cameraId) ?? []) {
    callback(camera);
  }
}

// Sibling components reach this through window rather than a relative import,
// because NiceGUI serves each component from its own hashed URL.
if (typeof window !== "undefined") {
  window.tooManyChefsCamera = {
    getCamera,
    subscribeCamera,
    worldToScreen,
    getTrack,
    subscribeTracks,
  };
}

export default {
  template: /*html*/ `
    <div class="sprite-canvas" style="line-height: 0;">
      <canvas
        ref="canvas"
        style="display: block; image-rendering: pixelated; image-rendering: crisp-edges;"
      ></canvas>
    </div>
  `,
  props: {
    renderables: { type: Array, default: () => [] },
    transform: {
      type: Object,
      default: () => ({ mode: "fixed", unit: 16, scale: 1 }),
    },
    backdrop: { type: Object, default: () => ({}) },
    frame: { type: Object, default: null },
    spriteSheets: { type: Object, default: () => ({}) },
    // Non-empty enables camera publishing for DOM overlays.
    cameraId: { type: String, default: "" },
    // Static layers opt out of the animation clock entirely.
    animated: { type: Boolean, default: true },
  },
  data() {
    return {
      tick: 0,
      frameHandle: null,
      startedAt: 0,
      dirty: true,
      previousById: {},
      transitionsById: {},
      hostWidth: 0,
      hostHeight: 0,
    };
  },
  mounted() {
    this.capturePrevious();
    this.loadSheets();
    this.observer = new ResizeObserver(() => {
      this.dirty = true;
      if (!this.animated) {
        this.draw();
      }
    });
    this.observer.observe(this.$el);
    this.startedAt = performance.now();
    if (this.animated) {
      this.startLoop();
    } else {
      this.$nextTick(() => this.draw());
    }
  },
  beforeUnmount() {
    if (this.frameHandle) {
      cancelAnimationFrame(this.frameHandle);
    }
    this.observer?.disconnect();
  },
  watch: {
    renderables: {
      deep: true,
      handler() {
        this.captureTransitions();
        this.dirty = true;
        if (!this.animated) {
          this.draw();
        }
      },
    },
    transform: {
      deep: true,
      handler() {
        this.dirty = true;
        if (!this.animated) {
          this.draw();
        }
      },
    },
    spriteSheets: {
      deep: true,
      handler() {
        this.loadSheets();
      },
    },
  },
  methods: {
    loadSheets() {
      const urls = Object.values(this.spriteSheets ?? {});
      Promise.all(urls.map(loadSheet)).then(() => {
        this.dirty = true;
        this.draw();
      });
    },

    startLoop() {
      const step = () => {
        const elapsed = performance.now() - this.startedAt;
        const tick = Math.floor((elapsed * TICKS_PER_SECOND) / 1000);
        if (tick !== this.tick) {
          this.tick = tick;
          this.dirty = true;
        }
        if (this.dirty) {
          this.draw();
        }
        this.frameHandle = requestAnimationFrame(step);
      };
      this.frameHandle = requestAnimationFrame(step);
    },

    capturePrevious() {
      const next = {};
      for (const renderable of this.renderables) {
        next[renderable.id] = { ...renderable };
      }
      this.previousById = next;
    },

    captureTransitions() {
      const next = {};
      for (const renderable of this.renderables) {
        next[renderable.id] = { ...renderable };
        const previous = this.previousById[renderable.id];
        const initFrames = renderable.sprite?.init_animation ?? [];
        if (!previous || initFrames.length === 0) {
          continue;
        }

        const changed =
          previous.x !== renderable.x ||
          previous.y !== renderable.y ||
          JSON.stringify(previous.sprite) !== JSON.stringify(renderable.sprite);
        if (!changed) {
          continue;
        }

        this.transitionsById[renderable.id] = {
          fromX: previous.x,
          fromY: previous.y,
          toX: renderable.x,
          toY: renderable.y,
          startedAtTick: this.tick,
          frameCount: initFrames.length,
        };
      }

      for (const id of Object.keys(this.transitionsById)) {
        if (!(id in next)) {
          delete this.transitionsById[id];
        }
      }

      this.previousById = next;
    },

    // Resolve the transform against the host element. Returns null when the
    // element has not been laid out yet.
    resolveCamera() {
      const transform = this.transform ?? {};
      const unit = transform.unit ?? 16;
      const gridWidth = Math.max(transform.grid_width ?? 1, 1);
      const gridHeight = Math.max(transform.grid_height ?? 1, 1);
      const contentWidth = gridWidth * unit;
      const contentHeight = gridHeight * unit;

      if ((transform.mode ?? "fixed") === "fixed") {
        const scale = Math.max(transform.scale ?? 1, 1);
        const pad = transform.pad ?? 0;
        const bufferWidth = contentWidth + pad * 2;
        const bufferHeight = contentHeight + pad * 2;
        return {
          unit,
          scale,
          originX: pad,
          originY: pad,
          bufferWidth,
          bufferHeight,
          cssWidth: bufferWidth * scale,
          cssHeight: bufferHeight * scale,
          overhang: pad * scale,
        };
      }

      const host = this.$el.getBoundingClientRect();
      if (host.width < 1 || host.height < 1) {
        return null;
      }

      const padding = unit * (transform.padding_cells ?? 0);
      const scale = Math.max(
        Math.floor(
          Math.min(
            host.width / (contentWidth + padding * 2),
            host.height / (contentHeight + padding * 2),
          ),
        ),
        1,
      );
      const bufferWidth = Math.ceil(host.width / scale);
      const bufferHeight = Math.ceil(host.height / scale);
      return {
        unit,
        scale,
        originX: Math.round((bufferWidth - contentWidth) / 2),
        originY: Math.round((bufferHeight - contentHeight) / 2),
        bufferWidth,
        bufferHeight,
        cssWidth: host.width,
        cssHeight: host.height,
        // A world canvas is already the size of the element it fills.
        overhang: 0,
      };
    },

    draw() {
      const canvas = this.$refs.canvas;
      if (!canvas) {
        return;
      }
      const camera = this.resolveCamera();
      if (!camera) {
        return;
      }
      this.dirty = false;

      // Reassigning width or height reallocates and clears the backing store,
      // so only touch it when the size actually moved.
      if (canvas.width !== camera.bufferWidth || canvas.height !== camera.bufferHeight) {
        canvas.width = camera.bufferWidth;
        canvas.height = camera.bufferHeight;
      }
      canvas.style.width = `${camera.cssWidth}px`;
      canvas.style.height = `${camera.cssHeight}px`;
      // The margin the canvas keeps for art that leaves its cell is pulled back
      // out of the layout, so the box a slot sees is the cell and the overhang
      // paints over whatever is outside it. Letting the padded buffer take part
      // in layout instead is what puts a lifted sprite back where it started: a
      // slot centring an item larger than itself lines the two up at the top
      // left rather than through the middle, and the cell goes down with it.
      canvas.style.margin = `${-camera.overhang}px`;

      if (this.cameraId) {
        publishCamera(this.cameraId, {
          unit: camera.unit,
          scale: camera.scale,
          originX: camera.originX,
          originY: camera.originY,
        });
      }

      const context = canvas.getContext("2d", { alpha: true });
      context.imageSmoothingEnabled = false;
      context.imageSmoothingQuality = "low";
      context.clearRect(0, 0, camera.bufferWidth, camera.bufferHeight);

      this.drawBackdrop(context, camera);

      const ordered = [...this.renderables].sort((left, right) => {
        if ((left.z ?? 0) !== (right.z ?? 0)) {
          return (left.z ?? 0) - (right.z ?? 0);
        }
        return (left.order ?? 0) - (right.order ?? 0);
      });

      if (this.frame) {
        context.save();
        this.framePath(context, camera);
        context.clip();
      }
      const positions = this.cameraId ? new Map() : null;
      for (const renderable of ordered) {
        const state = this.drawRenderable(context, renderable, camera);
        positions?.set(renderable.id, { x: state.x, y: state.y });
      }
      if (this.frame) {
        context.restore();
        // Two strokes form a dark outline around the warm wall rim.
        this.framePath(context, camera, this.frame.border_width / 2);
        context.strokeStyle = this.frame.edge;
        context.lineWidth = this.frame.border_width;
        context.stroke();
        this.framePath(context, camera, this.frame.border_width / 2);
        context.strokeStyle = this.frame.rim;
        context.lineWidth = Math.max(1, this.frame.border_width - 2);
        context.stroke();
      }
      if (positions) {
        publishTracks(this.cameraId, positions);
      }
    },

    framePath(context, camera, inset = 0) {
      const frame = this.frame;
      context.beginPath();
      context.roundRect(
        camera.originX + frame.x + inset,
        camera.originY + frame.y + inset,
        frame.width - inset * 2,
        frame.height - inset * 2,
        Math.max(0, frame.radius - inset),
      );
    },

    drawBackdrop(context, camera) {
      const backdrop = this.backdrop ?? {};
      if (backdrop.fill) {
        context.fillStyle = backdrop.fill;
        context.fillRect(0, 0, camera.bufferWidth, camera.bufferHeight);
      }
      if (!backdrop.checker) {
        return;
      }
      // Tile from the world origin so the pattern stays put across resizes.
      context.fillStyle = backdrop.checker;
      const unit = camera.unit;
      const startColumn = Math.floor(-camera.originX / unit);
      const endColumn = Math.ceil((camera.bufferWidth - camera.originX) / unit);
      const startRow = Math.floor(-camera.originY / unit);
      const endRow = Math.ceil((camera.bufferHeight - camera.originY) / unit);
      for (let column = startColumn; column < endColumn; column++) {
        for (let row = startRow; row < endRow; row++) {
          if (((column % 2) + (row % 2) + 2) % 2) {
            context.fillRect(
              camera.originX + column * unit,
              camera.originY + row * unit,
              unit,
              unit,
            );
          }
        }
      }
    },

    drawRenderable(context, renderable, camera) {
      const state = this.animatedState(renderable);
      const parts = state.frame?.parts ?? [];

      for (const part of parts) {
        const url = this.spriteSheets?.[part.sheet];
        const sheet = url ? SHEET_IMAGES.get(url) : undefined;
        if (!sheet) {
          continue;
        }
        context.drawImage(
          sheet,
          part.x,
          part.y,
          part.width,
          part.height,
          Math.round(camera.originX + state.x * camera.unit + part.shift_x),
          Math.round(camera.originY + state.y * camera.unit + part.shift_y),
          part.width,
          part.height,
        );
      }
      return state;
    },

    animatedState(renderable) {
      const transition = this.transitionsById[renderable.id];
      if (!transition) {
        return {
          frame: this.loopFrame(renderable.sprite),
          x: renderable.x,
          y: renderable.y,
        };
      }

      const initFrames = renderable.sprite?.init_animation ?? [];
      const frameIndex = this.tick - transition.startedAtTick;
      if (frameIndex < 0 || frameIndex >= initFrames.length) {
        delete this.transitionsById[renderable.id];
        return {
          frame: this.loopFrame(renderable.sprite),
          x: renderable.x,
          y: renderable.y,
        };
      }

      const progress =
        transition.frameCount <= 1 ? 1 : frameIndex / (transition.frameCount - 1);
      return {
        frame: initFrames[frameIndex],
        x: transition.fromX + (transition.toX - transition.fromX) * progress,
        y: transition.fromY + (transition.toY - transition.fromY) * progress,
      };
    },

    loopFrame(sprite) {
      const frames = sprite?.loop_cycle_animation ?? [];
      if (frames.length === 0) {
        return null;
      }
      return frames[this.tick % frames.length];
    },
  },
};
