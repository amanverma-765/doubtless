import type React from "react";
import { MediaPlayer, MediaProvider } from "@vidstack/react";
import {
  defaultLayoutIcons,
  DefaultVideoLayout,
} from "@vidstack/react/player/layouts/default";

interface VideoPlayerProps {
  playlistUrl: string;
  title?: string;
  poster?: string;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  playlistUrl,
  title,
  poster,
}) => {
  return (
    <div className="w-full h-full relative flex items-center justify-center bg-black overflow-hidden rounded-[10px]">
      <MediaPlayer
        src={playlistUrl}
        title={title}
        poster={poster}
        playsInline
        autoPlay
        storage="doubtless-player-storage"
        className="w-full h-full aspect-video relative"
      >
        <MediaProvider />
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
