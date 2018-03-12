#!/usr/bin/env python3

# Copyright 2018 Ian Leonard <antonlacon@gmail.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warrant of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public Liencese
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# Core modules
import subprocess as sp # Calling system programs
import os               # Collaborating with the Operating System
# Project modules
import bot_cfg          # Bot's config file


def vlc_play_audio(file):
    """ Play the given file or URL """

    # Only attempt to invoke VLC if bot_cfg.vlc_bin is valid path
    if os.path.isfile(bot_cfg.vlc_bin) and os.access (bot_cfg.vlc_bin, os.X_OK):
        # Invoke VLC without: error messages, interface, video playback
        # Close VLC when finished
        VLC_command=[
            bot_cfg.vlc_bin, "--quiet", "-I null", "--no-video",
            "--play-and-exit", file
            ]
        playback = sp.Popen(VLC_command)
        print(f"LOG: Playback started of {file}")
    else:
        print(f"ERR: VLC not found at {bot_cfg.vlc_bin} or incorrect permissions.")
