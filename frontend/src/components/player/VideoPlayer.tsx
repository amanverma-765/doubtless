import type React from "react";
import {
  MediaPlayer,
  MediaProvider,
  Poster,
  Track,
  type MediaPlayerInstance,
} from "@vidstack/react";
import {
  defaultLayoutIcons,
  DefaultVideoLayout,
} from "@vidstack/react/player/layouts/default";

export interface TextTrackItem {
  src: string;
  label?: string;
  language?: string;
  kind: "subtitles" | "captions" | "chapters" | "descriptions" | "metadata";
  default?: boolean;
}

interface VideoPlayerProps {
  playlistUrl: string;
  title?: string;
  poster?: string;
  tracks?: TextTrackItem[];
  playerRef?: React.RefObject<MediaPlayerInstance | null>;
  onTimeUpdate?: (time: number) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  playlistUrl,
  title,
  poster,
  tracks,
  playerRef,
  onTimeUpdate,
}) => {
  return (
    <div className="w-full h-full relative flex items-center justify-center bg-black overflow-hidden rounded-2xl">
      <MediaPlayer
        ref={playerRef}
        src={playlistUrl}
        title={title}
        playsInline
        autoPlay
        storage="doubtless-player-storage"
        className="w-full h-full aspect-video relative"
        onTimeUpdate={(detail) => {
          if (onTimeUpdate) {
            onTimeUpdate(detail.currentTime);
          }
        }}
      >
        <MediaProvider>
          {poster && (
            <Poster
              className="vds-poster"
              src={poster}
              alt={title || "Video thumbnail"}
            />
          )}
          {tracks?.map((track) => (
            <Track key={track.src} {...track} />
          ))}
        </MediaProvider>
        <DefaultVideoLayout
          icons={defaultLayoutIcons}
          slots={{
            pipButton: null,
            googleCastButton: null,
            airPlayButton: null,
          }}
        />
      </MediaPlayer>
    </div>
  );
};
