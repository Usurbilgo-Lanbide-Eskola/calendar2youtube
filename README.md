# Calendar2YouTube Service

This service creates a YouTube streaming event for the next event in a given Google Calendar calendar.
The calendar events can be filtered using a keyword.

## Installation

- Clone the repo into a temp folder:

> ```git clone https://github.com/Usurbilgo-Lanbide-Eskola/calendar2youtube.git /tmp/calendar2youtube && cd /tmp/calendar2youtube```

- Create the installation folder and move the appropiate files (edit the user):

> ```sudo mkdir /opt/calendar2youtube```

> ```sudo cp requirements.txt /opt/calendar2youtube```

> ```sudo cp -r src/* /opt/calendar2youtube```

> ```sudo cp systemd/calendar2youtube.service /etc/systemd/system/```

> ```sudo chown -R root:root /opt/calendar2youtube```

- Create the virtual environment and install the dependencies:

> ```cd /opt/calendar2youtube```

> ```sudo apt install -y python3-venv python3-dev ```

> ```python3 -m venv venv```

> ```source venv/bin/activate```

> ```pip install --upgrade pip```

> ```pip install -r requirements.txt```

- Place the ```credentials.json``` and ```token.pickle``` files and create the configuration file:

> ```nano .env```

> ```
> CLASSROOM_CALENDAR_ID=""
> CALENDAR2YOUTUBE_CALENDAR_ID=""
> STREAMING_KEYWORD=""
> LIVE_STREAM_TITLE=""
> ```



- Start the script

> ```sudo systemctl enable calendar2youtube.service && sudo systemctl start calendar2youtube.service```

## Author

(c) 2020 [Usurbilgo Lanbide Eskola](http://www.lhusurbil.eus/web/) ([Aitor Iturrioz](https://github.com/bodiroga))

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.