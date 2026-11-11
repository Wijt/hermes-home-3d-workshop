// The film's sound, as its own composition: a marimba bed with light hand percussion, written as notes, plus a few
// sounds on the picture's physical moments (a bubble landing, the press of Start, the part dropping into the box).
// It draws nothing, so it renders in seconds at a tiny size; tools/build_film.sh muxes its sound under the picture.
//
// The film's scenes start at (seconds): ask 0, title 6.5, make 11, approve 22.5, print 33.5, box 43.5, twist 53,
// groups 65.33, close 74.33, end 84.33. The tempo is 120: a beat is 0.5 s, so every cut up to the twist is on a beat.
// The arrangement was first written for a shorter cut (make ended at 18.5, the twist's last beat was 1.33 s
// shorter); those times are kept and moved onto the film's clock by `re` below, so read the bars as that cut's.
// Samples: the Versilian Community Sample Library (CC0), fetched with `raea sounds get` (see README).
import { AbsoluteFill, Composition, Mix, registerRoot, staticFile } from "raea";
import * as Tone from "raea/tone";

export const FILM_FRAMES = 2530;
const BEAT = 0.5;
const BAR = 2;

// ---------------------------------------------------------------------------------------------------------------
// Instruments
// ---------------------------------------------------------------------------------------------------------------
const room = new Tone.Reverb({ decay: 1.6, wet: 0.16 }).connect(Tone.buses.music);

const marimba = new Tone.Sampler({
  urls: {
    F1: staticFile("sounds/vcsl-marimba/F1.wav"),
    C2: staticFile("sounds/vcsl-marimba/C2.wav"),
    G2: staticFile("sounds/vcsl-marimba/G2.wav"),
    B2: staticFile("sounds/vcsl-marimba/B2.wav"),
    F3: staticFile("sounds/vcsl-marimba/F3.wav"),
    C4: staticFile("sounds/vcsl-marimba/C4.wav"),
    G4: staticFile("sounds/vcsl-marimba/G4.wav"),
    B4: staticFile("sounds/vcsl-marimba/B4.wav"),
    F5: staticFile("sounds/vcsl-marimba/F5.wav"),
    C6: staticFile("sounds/vcsl-marimba/C6.wav"),
  },
  release: 1,
  volume: 13, // the library's takes are quiet: this puts the marimba in front of the pad and the bass
}).connect(room);

const bass = new Tone.Synth({ oscillator: { type: "triangle" }, envelope: { attack: 0.012, decay: 0.35, sustain: 0.3, release: 0.3 }, volume: -20 }).connect(Tone.buses.music);
const pad = new Tone.PolySynth(Tone.Synth, { oscillator: { type: "triangle" }, envelope: { attack: 0.45, decay: 0.4, sustain: 0.75, release: 1.6 }, volume: -33 }).connect(room);

const hit = (file: string, volume: number) => {
  const p = new Tone.Player(staticFile(file)).connect(Tone.buses.music);
  p.volume.value = volume;
  return p;
};
// the cajon is the kit: its low centre hit is the kick, its edge the backbeat
const kick = [hit("sounds/vcsl-cajon/Cajon_hit1_f_rr1.wav", -8), hit("sounds/vcsl-cajon/Cajon_hit1_f_rr2.wav", -8)];
const slap = [hit("sounds/vcsl-cajon/Cajon_hit2_mp_rr1.wav", -7), hit("sounds/vcsl-cajon/Cajon_hit3_mp_rr1.wav", -7)];
const shake = [hit("sounds/vcsl-shaker-small/Mid_ShakerHighFaster_Down_rr1.wav", -11), hit("sounds/vcsl-shaker-small/Mid_ShakerHighFaster_Up_rr1.wav", -14), hit("sounds/vcsl-shaker-small/Mid_ShakerHighFaster_Down_rr2.wav", -11), hit("sounds/vcsl-shaker-small/Mid_ShakerHighFaster_Up_rr2.wav", -14)];
const clap = [hit("sounds/vcsl-claps/Clap_rr1.wav", -8), hit("sounds/vcsl-claps/Clap_rr2.wav", -8)];
// sounds on the picture
const tick = [hit("sounds/vcsl-woodblock/wood_click_mp.wav", -12), hit("sounds/vcsl-woodblock/wood_click2_mp.wav", -12), hit("sounds/vcsl-woodblock/wood_click3_vl1.wav", -12)];
const press = hit("sounds/vcsl-woodblock/wood_click_ff.wav", -8);
const thunkWood = hit("sounds/vcsl-cajon/Cajon_hit1_fff_rr1.wav", -6);
const thunkLow = new Tone.MembraneSynth({ pitchDecay: 0.05, octaves: 3, envelope: { attack: 0.001, decay: 0.32, sustain: 0, release: 0.1 }, volume: -8 }).connect(Tone.buses.music);
const blip = new Tone.MembraneSynth({ pitchDecay: 0.025, octaves: 1.6, envelope: { attack: 0.001, decay: 0.13, sustain: 0, release: 0.06 }, volume: -19 }).connect(room);
const air = new Tone.NoiseSynth({ noise: { type: "pink" }, envelope: { attack: 0.5, decay: 0.08, sustain: 0, release: 0.06 }, volume: -22 }).connect(new Tone.Filter({ type: "highpass", frequency: 1800 }).connect(room));
const slide = new Tone.NoiseSynth({ noise: { type: "brown" }, envelope: { attack: 0.25, decay: 0.2, sustain: 0.6, release: 0.25 }, volume: -20 }).connect(new Tone.Filter({ type: "bandpass", frequency: 700, Q: 0.8 }).connect(Tone.buses.music));

// ---------------------------------------------------------------------------------------------------------------
// The tune: four bars that turn round (F, C over E, A minor, G), an eighth-note marimba figure, a short hook on top
// ---------------------------------------------------------------------------------------------------------------
const FIGURE = [
  ["F3", "C4", "A4", "C4", "G4", "C4", "A4", "C4"],
  ["E3", "C4", "G4", "C4", "E4", "C4", "G4", "C4"],
  ["A3", "E4", "G4", "E4", "C5", "E4", "G4", "E4"],
  ["G3", "D4", "B4", "D4", "G4", "D4", "B4", "D4"],
];
const ROOT = ["F2", "E2", "A2", "G2"];
const CHORD = [
  ["F3", "A3", "C4", "G4"],
  ["E3", "G3", "C4", "G4"],
  ["A3", "C4", "E4", "G4"],
  ["G3", "B3", "D4", "G4"],
];
// the hook: [beat in the bar, note], one list per bar of the four
const HOOK: Array<Array<[number, string]>> = [
  [[0, "A5"], [1, "G5"], [2, "E5"]],
  [[0, "G5"], [1.5, "E5"], [2, "D5"], [3, "C5"]],
  [[0, "E5"], [1, "D5"], [2, "C5"], [3.5, "D5"]],
  [[0, "D5"], [2, "B4"], [3, "D5"]],
];

type Note = { t: number; n: string | string[]; d: number; v: number };
const mar: Note[] = [];
const low: Note[] = [];
const pads: Note[] = [];
const drums: Array<{ t: number; p: Tone.Player }> = [];
let shakeTurn = 0;

type Bar = { figure?: number; hook?: boolean; bass?: boolean; pad?: boolean; kick?: boolean; back?: boolean; shaker?: boolean; clap?: boolean };

/** One bar starting at `t`, on chord `c` (0..3), with the parts named in `on`. `beats` < 4 writes a short bar. */
function bar(t: number, c: number, on: Bar, beats = 4) {
  const eighths = beats * 2;
  if (on.figure) {
    for (let i = 0; i < eighths; i++) {
      // the 3 + 3 + 2 accent of the figure; a quieter figure drops the weak notes
      const strong = i === 0 || i === 3 || i === 6;
      if (on.figure < 1 && !strong && i % 2 === 1) continue;
      mar.push({ t: t + i * BEAT * 0.5, n: FIGURE[c][i], d: 0.4, v: (strong ? 0.78 : 0.5) * Math.min(1, on.figure + 0.25) });
    }
  }
  if (on.hook) for (const [b, n] of HOOK[c]) if (b < beats) mar.push({ t: t + b * BEAT, n, d: 0.6, v: 0.86 });
  if (on.bass) {
    low.push({ t, n: ROOT[c], d: Math.min(beats, 2.8) * BEAT, v: 0.9 });
    if (beats >= 4) low.push({ t: t + 3.5 * BEAT, n: ROOT[c], d: 0.2, v: 0.7 });
  }
  if (on.pad) pads.push({ t, n: CHORD[c], d: beats * BEAT - 0.1, v: 0.6 });
  for (let b = 0; b < beats; b++) {
    if (on.kick && (b === 0 || b === 2)) drums.push({ t: t + b * BEAT, p: kick[(b / 2) % 2] });
    if (on.back && (b === 1 || b === 3)) drums.push({ t: t + b * BEAT, p: slap[b === 1 ? 0 : 1] });
    if (on.clap && b === 3) drums.push({ t: t + b * BEAT, p: clap[Math.round(t) % 2] });
    if (on.shaker) for (let e = 0; e < 2; e++) drums.push({ t: t + (b + e * 0.5) * BEAT, p: shake[shakeTurn++ % 4] });
  }
}

const FULL: Bar = { figure: 1, hook: true, bass: true, pad: true, kick: true, back: true, shaker: true };
const GROOVE: Bar = { figure: 1, bass: true, pad: true, kick: true, back: true, shaker: true };
const LIGHT: Bar = { figure: 0.5, bass: true, pad: true, shaker: true };
const THIN: Bar = { figure: 0.5, pad: true };

// ask (0 to 6.5): a held chord and a few marimba notes, like messages arriving
pads.push({ t: 0.1, n: CHORD[0], d: 3.0, v: 0.6 }, { t: 3.2, n: CHORD[1], d: 3.1, v: 0.6 });
for (const [t, n] of [[0.5, "C5"], [1.5, "A4"], [2.5, "G4"], [3.5, "E5"], [4.5, "G4"], [5.25, "C5"], [5.75, "E5"], [6.0, "G5"], [6.25, "A5"]] as Array<[number, string]>) mar.push({ t, n, d: 0.5, v: 0.6 });

// title (6.5 to 11): the tune arrives with the red
bar(6.5, 0, FULL);
bar(8.5, 1, FULL);
bar(10.5, 2, { ...FULL, clap: true }, 1); // one beat, then the cut to make
// make (11 to 18.5)
bar(11, 2, GROOVE, 3);
bar(12.5, 3, GROOVE);
bar(14.5, 0, FULL);
bar(16.5, 3, { ...FULL, clap: true }); // the bar before approve (20.5 on the film's clock)
// approve (18.5 to 29.5): the band steps back while a person decides
bar(18.5, 2, THIN);
bar(20.5, 3, THIN);
bar(22.5, 0, { ...THIN, bass: true });
bar(24.5, 1, { pad: true, bass: true }, 2); // two beats of air before the press at 25.5
// the press at 25.5, then the tune comes back as the print starts
bar(26.5, 0, FULL);
bar(28.5, 1, { ...FULL, clap: true }, 2);
// print (29.5 to 39.5)
bar(29.5, 2, FULL);
bar(31.5, 3, FULL);
bar(33.5, 0, FULL);
bar(35.5, 1, { ...FULL, clap: true });
bar(37.5, 2, { pad: true, bass: true }); // "Finished": the band stops, one bell
// box (39.5 to 49)
bar(39.5, 3, LIGHT);
bar(41.5, 0, LIGHT);
bar(43.5, 1, LIGHT);
// the tagline lands at 45.5
bar(45.5, 0, FULL);
bar(47.5, 1, { ...FULL, clap: true }, 3);
// twist (49 to 60): no beat, a low chord under real photos
pads.push({ t: 49, n: ["A2", "E3", "A3", "C4"], d: 5.4, v: 0.75 }, { t: 54.67, n: ["F2", "C3", "F3", "A3"], d: 2.5, v: 0.75 }, { t: 57.33, n: ["C3", "G3", "C4", "E4"], d: 1.5, v: 0.75 }, { t: 59, n: ["G2", "D3", "G3", "B3"], d: 0.9, v: 0.75 });
low.push({ t: 49, n: "A2", d: 5.2, v: 0.5 }, { t: 54.67, n: "F2", d: 2.4, v: 0.5 }, { t: 57.33, n: "C3", d: 1.5, v: 0.5 }, { t: 59, n: "G2", d: 0.9, v: 0.5 });
for (const [t, n] of [[49.5, "E4"], [50.5, "A4"], [51.67, "C5"], [52.67, "B4"], [53.67, "A4"], [54.67, "C5"], [55.33, "F5"], [56, "A5"], [57.33, "G5"], [57.83, "E5"], [58.33, "C5"], [59, "D5"], [59.25, "G5"], [59.5, "B5"], [59.75, "D6"]] as Array<[number, string]>) mar.push({ t, n, d: 0.7, v: 0.8 });
// groups (60 to 69)
bar(60, 0, FULL);
bar(62, 1, FULL);
bar(64, 2, GROOVE);
bar(66, 3, GROOVE);
bar(68, 0, { ...FULL, clap: true }, 2);
// close (69 to 79): the tune once more, then it comes to rest on C
bar(69, 0, FULL);
bar(71, 1, FULL);
bar(73, 2, { figure: 1, hook: true, bass: true, pad: true, shaker: true });
bar(75, 3, { figure: 0.5, bass: true, pad: true }, 2);
pads.push({ t: 76, n: ["C3", "G3", "C4", "E4"], d: 2.2, v: 0.7 });
low.push({ t: 76, n: "C2", d: 2.0, v: 0.9 });
for (const [i, n] of ["C4", "E4", "G4", "C5", "E5", "G5", "C6"].entries()) mar.push({ t: 76 + i * 0.125, n, d: 1.2, v: 0.5 + i * 0.05 });

// ---------------------------------------------------------------------------------------------------------------
// Onto the film's clock. make is two bars (4 s) longer than in the first cut and the twist's last beat 1.33 s longer.
// ---------------------------------------------------------------------------------------------------------------
const re = (t: number) => (t < 16.5 ? t : t < 58.9 ? t + 4 : t + 16 / 3);
for (const e of [...mar, ...low, ...pads]) e.t = re(e.t);
for (const d of drums) d.t = re(d.t);
// from here on, times are the film's own
// make's two new bars
bar(16.5, 1, GROOVE);
bar(18.5, 2, FULL);
// the three options arrive
for (const [t, n] of [[11.53, "E5"], [11.7, "G5"], [11.87, "A5"]] as Array<[number, string]>) mar.push({ t, n, d: 0.4, v: 0.5 });
// the layers lift apart at 16.9 and close at 18.5: a run up, a run down
for (const [i, n] of ["C5", "D5", "E5", "G5", "A5", "C6"].entries()) mar.push({ t: 16.93 + i * 0.11, n, d: 0.5, v: 0.55 + i * 0.05 });
for (const [i, n] of ["C6", "A5", "G5", "E5"].entries()) mar.push({ t: 18.47 + i * 0.12, n, d: 0.5, v: 0.7 - i * 0.05 });
// the twist's last beat (real footage): the C chord holds, three more notes
pads.push({ t: 62.9, n: ["C3", "G3", "C4", "E4"], d: 1.3, v: 0.75 });
low.push({ t: 62.9, n: "C3", d: 1.3, v: 0.5 });
for (const [t, n] of [[63.0, "E5"], [63.5, "G5"], [63.85, "C6"]] as Array<[number, string]>) mar.push({ t, n, d: 0.7, v: 0.8 });
for (const a of [mar, low, pads]) a.sort((x, y) => x.t - y.t);
drums.sort((x, y) => x.t - y.t);

// ---------------------------------------------------------------------------------------------------------------
// Sounds on the picture (seconds of the film; the ones passed through `re` were timed on the first cut)
// ---------------------------------------------------------------------------------------------------------------
/** a bubble landing */
const POPS: Array<[number, string]> = [
  ...([[0.3, "E5"], [3.25, "A4"], [43.45, "A4"], [60.12, "E5"], [61.02, "A4"], [65.35, "C5"]] as Array<[number, string]>).map(([t, n]) => [re(t), n] as [number, string]),
  [12.8, "E5"], // Mum picks the second one
  [19.9, "A4"], // the blue note
  [38.97, "A4"], // Mıstık tells Mum the print has started
  [61.73, "E5"], // the owner's line
];
POPS.sort((x, y) => x[0] - y[0]);
/** a small thing arriving: a tool's name, a mark, a counted number */
const TICKS = [...[51.87, 52.03, 52.2, 64.35, 64.62, 64.88, 70.67].map(re), 11.2, 13.2, 14.2, 16.67, 19.5, 63.27].sort((x, y) => x - y);
/** air before a colour takes the frame: [start, length] */
const AIRS: Array<[number, number]> = ([[5.85, 0.6], [10.5, 0.45], [18.0, 0.45], [32.7, 0.45], [59.4, 0.55]] as Array<[number, number]>).map(([t, d]) => [re(t), d] as [number, number]);
const PRESS = re(25.5);
const FINISHED = re(37.85);
const SLIDE: [number, number] = [re(41.4), 1.2];
const THUNK = re(42.8);

new Tone.Part((t, e: Note) => marimba.triggerAttackRelease(e.n, e.d, t, e.v), mar.map((e) => [e.t, e] as [number, Note])).start(0);
new Tone.Part((t, e: Note) => bass.triggerAttackRelease(e.n as string, e.d, t, e.v), low.map((e) => [e.t, e] as [number, Note])).start(0);
new Tone.Part((t, e: Note) => pad.triggerAttackRelease(e.n, e.d, t, e.v), pads.map((e) => [e.t, e] as [number, Note])).start(0);
new Tone.Part((t, e: { p: Tone.Player }) => e.p.start(t), drums.map((e) => [e.t, e] as [number, { p: Tone.Player }])).start(0);
new Tone.Part((t, n: string) => blip.triggerAttackRelease(n, 0.12, t), POPS).start(0);
new Tone.Part((t, i: number) => tick[i % 3].start(t), TICKS.map((t, i) => [t, i] as [number, number])).start(0);
new Tone.Part((t, d: number) => air.triggerAttackRelease(d, t), AIRS).start(0);
Tone.getTransport().schedule((t) => { press.start(t); thunkLow.triggerAttackRelease("G1", 0.2, t); }, PRESS);
Tone.getTransport().schedule((t) => marimba.triggerAttackRelease(["G5", "C6"], 1.4, t, 0.9), FINISHED);
Tone.getTransport().schedule((t) => slide.triggerAttackRelease(SLIDE[1], t), SLIDE[0]);
Tone.getTransport().schedule((t) => { thunkWood.start(t); thunkLow.triggerAttackRelease("C2", 0.3, t); }, THUNK);
// the last chord rings out
Tone.buses.music.volume.rampTo(-40, 1.6, re(77.3));
Tone.getTransport().bpm.value = 120;
Tone.getTransport().start();

function Sound() {
  return (
    <AbsoluteFill style={{ background: "#121316" }}>
      <Mix lufs={-14} ceiling={-1.5} />
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="sound" component={Sound} width={320} height={180} fps={30} durationInFrames={FILM_FRAMES} />);
