I have hours of video of myself around 13 years old. Could I construct a generative model of my voice with that

Yes—probably, with a big caveat:

If the videos contain **clean enough speech audio**, you could likely train or adapt a voice model that sounds like **your 13-year-old voice**.

What matters most is not the video itself, but the **audio quality and amount of isolated speech**.

What you’d need:

- lots of **clear speech**
- minimal background music/noise
- enough variation in words, tone, pacinxqg
- ideally many minutes to hours of **you speaking alone**

What’s realistic:

- **Voice cloning / TTS voice replica:** very plausible if the audio is decent
- **A model of how you “would have spoken” in new sentences at 13:** also plausible
- **Perfect recovery of your exact historical voice:** not guaranteed; it will be an approximation shaped by the source quality and model choice

Main constraints:

- if the recordings are camcorder-quality, noisy, reverberant, or have other people talking over you, results drop fast
- puberty-era voices can be less stable, so your voice may vary across clips
- if you only have a little clean speech, you may get something recognizable but not highly faithful

Best path:

1. extract audio from the videos
2. isolate segments where only you are speaking
3. transcribe them
4. clean the audio
5. use that dataset to fine-tune or condition a voice model

Important caution:

- cloning your own voice is one thing
- using it to impersonate “present you” or fool others crosses into risky territory
- keep it clearly labeled as a reconstructed archival voice

A simpler framing is:  
You are not really building “a generative model of my voice from age 13” out of raw video alone. You are building **a speech dataset from those videos**, then using that to train or adapt a **voice synthesis model**.

If you want, I can outline the most practical workflow for doing this on a home PC without making it a giant ML research project.