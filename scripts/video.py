

class Video:
    """
     Video of a specific task performed by a specific signer in a specific session in LSFB.

    Args:
        session: The ID of the session that contains multiple records.
        task: The ID of the record. A record may contain multiple channels.
        angle: The angle used to record this video.
        signer: The ID of the signer in the video.
        signer_letter: Indicate the interlocutor (A or B)
        video_format: The format of the video (example: mp4)
        video_filename: The name of the video file.
        eaf_filename: The name of the ELAN file that contains this channel.

    Properties:
        tiers: Dictionary containing the names of the tiers in the ELAN file.
        annotations: Dictionary containing the annotations of each tier.

    Example: video "CLSFBI0702A_S015_B.mp4"
        session: 7
        task: 2
        angle: A
        signer: 15
        signer_letter: B
        video_format: mp4
        video_filename: CLSFBI0702A_S015_B.mp4
        eaf_filename: CLSFBI0702.eaf
    """

    def __init__(
            self,
            session: int,
            task: int,
            angle: str,
            signer: int,
            signer_letter: str,
            video_format: str,
            video_filename: str,
            eaf_filename: str,
    ):
        self.session = session
        self.task = task
        self.angle = angle
        self.signer = signer
        self.signer_letter = signer_letter
        self.video_format = video_format
        self.video_filename = video_filename
        self.eaf_filename = eaf_filename

        self.tiers = {
            'left': None,
            'right': None,
            'subtitles': None,
            'left-variations': None,
            'right-variations': None
        }

        self.annotations = {
            'left': None,
            'right': None,
            'subtitles': None,
            'left-variations': None,
            'right-variations': None
        }

    @property
    def eaf_path(self):
        return f'CLSFBI{self.session}/{self.eaf_filename}'

    def __str__(self):
        return f"""Video(eaf_path="{self.eaf_filename}", video_path="{self.video_filename}")"""

    def __repr__(self):
        return self.__str__()
