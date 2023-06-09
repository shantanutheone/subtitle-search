import srt
with open("Breaking.Bad_.S01E01.720p.BluRay.X264-REWARD.srt", 'r') as file:
    content = file.read()
    subs = srt.parse(content)
    print(subs)
    subtitle_data = []
    for i, subtitle in enumerate(subs):
        data = {
            'line_id': i + 1,
            'start_time': subtitle.start.total_seconds(),
            'end_time': subtitle.end.total_seconds(),
            'text': subtitle.content
        }
        subtitle_data.append(data)
    print(subtitle_data[0])