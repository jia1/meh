### Meh / 目 (め)

An automatic cyber spotter for illegal wildlife trade.

This project is my submission to the Indeed Summer Hackathon 2020.

### Motivation

I am interested in the conservation of wildlife. I got to know about the Cyber Spotting programme through WWF SG's Tiger Day webinar. After some googling, I found the following excerpt from [ifaw](https://www.ifaw.org/press-releases/tech-companies-wildlife-trafficking-online):

> So far, Coalition Cyber Spotters in the U.S., Germany and Singapore have flagged over 4,000 prohibited listings for sale online. … Through the program, Cyber Spotters have helped uncover new seller keywords and identify wildlife trafficking trends that have helped companies’ ongoing monitoring efforts.

Now, what if we can automate this? (And you should know where I am getting at.)

I am not aware of any ongoing projects similar to this. I am open to volunteering to such ongoing initiatives if my skills will come in handy.

### Prerequisites

- Python 3.6 or higher (I use Python 3.8)
- `pip`
- `brew`

### Setup instructions

Clone the repository and install the necessary Python packages:
```
git clone https://github.com/jia1/meh.git
cd meh/
pip3 install -r requirements.txt
```

Call the `make` command in `darknet`:
```
cd darknet/
make
```
Then, set `OPENCV=1` in `Makefile`.

Install the following `brew` packages:
```
brew install pkg-config
brew install opencv@2
```
The steps below may not help if you are installing `opencv@4`.

Add the following lines to your `~/.bash_profile` where applicable:
```
# For compilers to find opencv@2 you may need to set:
export LDFLAGS="-L/usr/local/opt/opencv@2/lib"
export CPPFLAGS="-I/usr/local/opt/opencv@2/include"

# For pkg-config to find opencv@2 you may need to set:
export PKG_CONFIG_PATH="/usr/local/opt/opencv@2/lib/pkgconfig"
```

Run the `predict` convenience script to check if your installation is correct:
```
. predict <ANY IMAGE LOCATED IN meh/>
```

Done.
