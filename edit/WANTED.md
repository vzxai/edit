# clips to fetch

The edit has a slot for each of these. Until a clip exists in `footage/news/`, its slot plays a stand-in:
Creative Commons footage, with the speaker's words typed out on screen for dialogue clips.
As soon as the file lands, the real footage takes over. It is cut on the words, subtitled and credited automatically.

The song goes in `music/i-feel-weird.mp3`, and `tools/fetch_wanted.py` grabs that too.

## for the agent on your computer

Paste this into Claude Code (or any coding agent) on a computer with normal internet:

```
Project: a TikTok edit in the git repo vzxai/edit, branch claude/tiktok-reels-end-times-edit-yy06q4.

1. Get the code. If that branch isn't on GitHub yet, I'll give you a git bundle file
   (seize-the-future.bundle). In a clone of vzxai/edit, run:
     git fetch <path-to>/seize-the-future.bundle claude/tiktok-reels-end-times-edit-yy06q4:claude/tiktok-reels-end-times-edit-yy06q4
     git checkout claude/tiktok-reels-end-times-edit-yy06q4
   (or, with no clone: git clone -b claude/tiktok-reels-end-times-edit-yy06q4 <path-to>/seize-the-future.bundle edit
   then set the remote to https://github.com/vzxai/edit)
2. Make sure ffmpeg is installed, then: pip install -U yt-dlp
3. Run: python tools/fetch_wanted.py
   It downloads the song and every priority-A clip listed in edit/wanted.json into footage/news/.
4. Read the report at the end.
   - "pick": the video is long. Open footage/_proxy/<id>_sheet.jpg (labelled frames), find where the
     moment in edit/wanted.json starts, then run:
     python tools/fetch_wanted.py --only <id> --url <url> --start m:ss
   - "missing": search for it yourself (YouTube, news sites, C-SPAN, the White House's channel).
     Once you have a URL: python tools/fetch_wanted.py --only <id> --url <url> [--start m:ss]
   Check each dialogue clip really contains the words in edit/wanted.json. Look at a few frames:
     ffmpeg -i footage/news/<id>.mp4 -vf fps=1 /tmp/<id>_%02d.jpg
   Also read the captions in footage/news/<id>.vtt. Don't keep anything graphic (no bodies, no blood).
5. If there's time: python tools/fetch_wanted.py --all (the priority-B extras).
6. Commit and push:
     git add footage/news music edit/wanted.json
     git commit -m "Add footage and song for the edit"
     git push -u origin claude/tiktok-reels-end-times-edit-yy06q4
   Then tell me what you couldn't find.
```

Then tell Claude in the cloud session that it's pushed. It pulls the branch, runs `./make.sh music/i-feel-weird.mp3`,
checks every clip against its words, and cuts the edit to the song.

## priority A (the cut needs these)

| id | what | words to find | part |
|---|---|---|---|
| `bezos_paid` | Jeff Bezos at the post-flight press conference, West Texas, July 20 2021, thanking Amazon workers and customers. | I also want to thank every Amazon employee and every Amazon customer, because you guys paid for all this. | I · i feel weird |
| `zuck_friends` | Mark Zuckerberg on AI companions, Dwarkesh Patel podcast, April 2025. | The average American, I think, has fewer than three friends. | I · i feel weird |
| `perry_kiss` | Katy Perry kneels and kisses the ground after landing from the all-female Blue Origin flight, April 14 2025. | b-roll | I · i feel weird |
| `musk_chainsaw` | Elon Musk holds up a chainsaw on stage at CPAC, Feb 20 2025 ('this is the chainsaw for bureaucracy'). | “chainsaw for bureaucracy” | I · i feel weird |
| `robot_marathon` | Humanoid robots running (and falling) in the Beijing half marathon, April 19 2025. | b-roll | I · i feel weird |
| `friend_ads` | The Friend AI pendant subway ads in New York covered in graffiti ('AI wouldn't care if you lived or died', 'stop profiting off of loneliness'), fall 2025. Any clear shot of defaced ads. | b-roll | I · i feel weird |
| `inauguration_ceos` | Tech CEOs lined up at the inauguration, Jan 20 2025 (Bezos, Zuckerberg, Musk, Pichai, Cook). | b-roll | II · their plan is to leave |
| `thiel_endure` | Ross Douthat asks Peter Thiel whether he'd prefer the human race to endure; Thiel hesitates (Interesting Times, NYT Opinion, June 26 2025). Keep the whole hesitation. | Douthat: You would prefer the human race to endure, right? Thiel: Uh... Douthat: You're hesitating. ... This is a long hesitation. | II · their plan is to leave |
| `karp_kill` | Palantir CEO Alex Karp on the Q4 2024 earnings call, Feb 3 2025. | ...and when it's necessary, to scare our enemies and, on occasion, kill them. | II · their plan is to leave |
| `ice_masked` | Masked federal immigration agents detaining someone on a street, 2025-2026 (news footage, not graphic). | b-roll | II · their plan is to leave |
| `la_fire` | Pacific Palisades fire, Jan 2025: houses burning, orange sky. | b-roll | II · their plan is to leave |
| `stargate_announce` | The Stargate announcement at the White House, Jan 21 2025 (Trump with Altman, Ellison, Son): the $500 billion line. | “500 billion” | III · super |
| `hinton_nobel` | Geoffrey Hinton's Nobel banquet speech, Stockholm, Dec 10 2024. | We urgently need research on how to prevent these new beings from wanting to take control. | III · super |
| `trump_si` | Trump at the White House, Sept 29 2026, after the tech leaders' lunch and the order renaming AI. | We've changed the name officially to SI. SI instead of AI... You know what that means? 'Super.' That's quite an announcement. | III · super |
| `trump_selfpolice` | Same day, outside the West Wing, on the AI accord. | I think I'm seeing tremendous self-policing. And they understand that they have to self-police. | III · super |
| `huang_zero` | Nvidia CEO Jensen Huang to CBS News (Jo Ling Kent), Sept 2026. | 2030 is not going to be the end of the world. There is zero percent chance that's going to be the end of the world. | III · super |
| `nepal_genz` | Nepal's Gen Z protest at parliament, Kathmandu, Sept 8 2025, with the One Piece straw-hat flag. Crowds and flags, nothing graphic. | b-roll | V · seize the future |
| `nepal_cleanup` | Young Nepalis sweeping and cleaning the streets after the protests, Sept 2025. | b-roll | V · seize the future |
| `onepiece_world` | The One Piece flag at Gen Z protests elsewhere: Indonesia (Aug 2025), Madagascar, Peru, the Philippines, Morocco GenZ212. | b-roll | V · seize the future |
| `serbia_silence` | Serbian students' 16 minutes of silence: a huge crowd standing still (Belgrade or Novi Sad, 2025). Aerials are best. | b-roll | V · seize the future |
| `srilanka_palace` | Aragalaya, Colombo, July 9 2022: crowds pour into the presidential palace after the president flees; people swim in his pool. Crowds and the occupied palace, nothing violent. | b-roll | V · seize the future |
| `bangladesh_aug5` | Dhaka, Aug 5 2024: huge crowds celebrate in the streets as the student uprising forces Sheikh Hasina out. | b-roll | V · seize the future |

## priority B (extras, if they turn up)

| id | what | words to find | part |
|---|---|---|---|
| `trump_unga` | Trump at the UN General Assembly, Sept 22 2026, announcing the rename. | ...the much more accurate term 'super' as opposed to 'artificial.' So it's super intelligence. | III · super |
| `amodei_risks` | Dario Amodei at the White House, Sept 29 2026. | The technology has very real risks. | III · super |
| `vance_frankenstein` | JD Vance on the All-In podcast, Sept 2026. | If you're building Frankenstein, stop. | III · super |
| `trump_hoax_call` | Trump phoning in to Jensen Huang on stage at the All-In Summit, Sept 14 2026, calling AI fears a hoax. | “hoax” | III · super |
| `doomsday_clock` | The Doomsday Clock unveiled at 85 seconds to midnight, Jan 27 2026. | “85 seconds” | II · their plan is to leave |
| `musk_demon` | Elon Musk at MIT, Oct 2014. | With artificial intelligence, we are summoning the demon. | III · super |
| `guard_la` | National Guard troops deployed in Los Angeles, June 2025. | b-roll | II · their plan is to leave |
| `ban_asi` | Sanders and Casar introduce the Ban Artificial Superintelligence Act, Sept 23 2026. | b-roll | V · seize the future |
| `india_genz` | India's Gen Z protests over the exam paper leaks, 2026. | b-roll | V · seize the future |
| `italy_general_strike` | Italy's general strike for Gaza, Oct 3 2025: ports and city centres full of marching workers. | b-roll | V · seize the future |
| `kenya_genz` | Kenya's Gen Z protests against the Finance Bill, June 2024: crowds marching in Nairobi (crowds only). | b-roll | V · seize the future |
