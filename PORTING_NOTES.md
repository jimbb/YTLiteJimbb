# Porting notes: YouTube 21.x

This fork builds **YTLite 3.0.1** from source (dayanch96's last open-source release, March 2024). Releases 4.0 through 5.2.2 were binary-only, so their fixes were re-implemented here from the public release notes, a dump of YouTube 21.38.2's Objective-C metadata, and [YouMod](https://github.com/Tonwalter888/YouMod) (GPL-3.0).

- **Target:** YouTube 21.38.2 (needs iOS 17+), sideloaded through LiveContainer.
- **Status:** every hook and API call below was checked against the 21.38.2 binary; **none of it has been tested on a device yet**.

## What the build contains

`Create YouTube Plus app` (main.yml) builds YTLite from this repo, plus these optional add-ons (all cloned from their latest commit at build time):

| Add-on | Source | Default |
|---|---|---|
| YouTube-X (ads, background play) | PoomSmart/YouTube-X | **on** |
| YouPiP, YouQuality, Return YouTube Dislikes, YTABConfig | PoomSmart | off |
| YTUHD (built with `SIDELOAD=1`, bundled libvpx/dav1d) | PoomSmart/YTUHD | off |
| DontEatMyContent | therealFoxster | off |

The decrypted IPA can be passed as a draft-release tag (e.g. `ipa-21.38.2`) instead of a public URL.

## Fixed for 21.x

| Area | What changed in YouTube | Fix | Source |
|---|---|---|---|
| Promo throttle, settings (hints, cast discovery), content warning, classic quality, extra speeds, menu items, resume-to-Shorts, pivot bar | Classes split into protocol + `…Impl` | `%init` remap, old class preferred | own analysis |
| Default quality/speed, auto fullscreen, Shorts→regular, captions off | `loadWithPlayerTransition:playbackConfig:` gone | hook `prepareToLoadWithPlayerTransition:expectedLayout:` | own analysis, matches PoomSmart/YTAutoFullScreen |
| Hold to speed | `scrubUserEducationView` moved to `YTDoubleTapToSeekController` (**crash**) | look it up there | own analysis |
| Disable auto captions | `setActiveCaptionTrack:` → `…:source:` (**crash**) | call new selector with `source:0` | own analysis, YouMod uses the same |
| Pause on overlay | controls view lost `playerViewController` (**crash**) | responder-chain lookup | own analysis |
| Copy video info | `playerResponse` → `contentPlayerResponse`; fixed-depth VC chain | walk up to the owner of `playerViewController` | own analysis |
| Native share | protobuf 28+: no extension class methods, no `-unknownFields` (**crash**) | extensions by `singletonName`, `GPBUnknownFields` | own analysis |
| Speeds > 2x | app-version spoof to 18.18.2 (4.0 removed it, 5.1 called spoofing broken) | spoof removed; lift `maximumPlaybackRate` / `maximumSupportedPlaybackRate` / `YTIPlayerHotConfig` | release notes + YouMod |
| Show end time | `YTSingleVideoController.playbackRate` gone | `activePlaybackRateModel.rate` | own analysis |
| Force miniplayer | `YTWatchMiniBarViewController` gone | `YTWatchFloatingMiniplayerViewController` | own analysis |
| Don't snap to chapter, red/gray progress bar | new modular player bar | `YTModularPlayerBarController`, `YTPlayerBarSegmentView` | own analysis |
| Disable free zoom | flag renamed | `videoZoomFreeZoomEnabled` | own analysis |
| Ad signals | moved to `YTAdShieldUtils`; nil unsafe | remap, return `@{}` | own analysis, YouTube-X |
| Shorts like/comment/share/remix/pivot buttons | action bar is now Elements (ASDK) | match accessibility ids, remove from yoga parent | YouMod |
| New feed ads | `eml.ad_layout.*` elements | clear the cell's yoga children | YouMod |
| Sideload playback error 14 | "An error occurred" | reload the video once | YouMod (from Mark02-2012/YTPlaybackFix) |
| Build | newer clang `-Werror`; protobuf HEAD dropped `GPBUnknownFieldSet` | indentation fix; protobuf pinned to v25.3 | — |

## Left out

### New features from YTLite 4.0–5.2.2 (not ported)
These are features, not fixes, and each is its own project:

- **Downloads**: video, audio, captions, thumbnails, multi-download, resume.
- **SponsorBlock**: segments, whitelist, user IDs.
- **Gestures**: player gestures (brightness, volume, seek on either side), tap/swipe to seek, and hold-to-speed in Shorts.
- **Settings UI**: rewrite and search, import/export, account system.
- **Themes**: OLED theme and keyboard, logo selector, custom startup animation.
- **Tab bar**: reordering, extra tabs (Watch later, History, Posts, Hype, Music, Live…), translucent bar.
- **Tools**: sleep timer, Discord RPC, post and comment translation, image viewer, external players (Infuse/VLC), Control Center seek, clipboard link opener, link tracking removal.
- **Preferences**: preferred audio track and caption language, excluding auto-dubbed tracks, remember loop mode.
- **Custom speed engine** (up to 10x with a slider).

YouMod implements many of these in open source (downloads up to 1080p60, SponsorBlock, translation, OLED, tab reordering, audio track selection), so any of them can be ported from there with GPL-3.0 attribution.

### Existing options that no longer work on 21.38.2
YouTube removed the thing these toggle, so there is nothing to hook:

| Option (key) | Removed in YouTube |
|---|---|
| Hide comment sort chips (`hideSortComments`) | `YTColdConfig enableChipsInTheCommentsHeaderIos` |
| Stock volume HUD (`stockVolumeHUD`) | `YTColdConfig iosUseSystemVolumeControlInFullscreen` |
| Swipe right to dismiss panel in landscape (always on) | `isLandscapeEngagementPanelSwipeRightToDismissEnabled` |
| Use app theme setting (always on) | `shouldUseAppThemeSetting`; `iosUseAppThemeSettingV3` exists but is untested, so it isn't hooked |
| Shorts header items: channel name, description/title, audio track, promo card, thanks badge, source link (`hideShortsChannelName`, `hideShortsDescription`, `hideShortsAudioTrack`, `hideShortsPromoCards`, `hideShortsThanks`, `hideShortsSource`) | `YTReelWatchHeaderView` setters; now Elements, and no accessibility ids are known yet (needs inspecting the live Shorts screen) |
| Part of the Shorts progress bar (`shortsProgress`) | `mobileShortsTabInlined`, `enablePlayerBarForVerticalVideoWhenControlsHiddenInFullscreen` (the player-bar hooks still exist) |
| Fit Shorts button labels | `YTReelPlayerButton` (cosmetic) |

### Unverified, check on device first
- Shorts **dislike** hiding uses `id.reel_dislike_button`, which is a guess; YouMod has no dislike id.
- Speeds above 2x rely on the rate-cap hooks. If a speed still caps at 2x, try YouMod's `YTIGranularVariableSpeedConfig` override. It is not ported because its type encoding is inconsistent (`%new(d@:)` returning `int`).
- Force miniplayer, snap to chapter, and red progress bar all use replacement classes found by name. The methods exist, but their behaviour hasn't been seen on a device.

### Add-on gaps (third-party code, picked up automatically when the authors fix them)
- **Return YouTube Dislikes:** Shorts dislike counts (`YTReelWatchLikesController updateLikeButtonWithRenderer:` is gone).
- **DontEatMyContent:** `YTMainAppEngagementPanelViewController`, `YTVideoZoomOverlayView` and `YTWatchMiniBarViewController` are gone, so it only partly works.
- **YouPiP / YTUHD:** only legacy multi-version hooks are dead. The current paths (`MLPIPControllerImpl`, the `preferredOutputFormats:` decoder factory) are present.

### Ads not covered
YTLite `noAds`, YouTube-X and the `eml.ad_layout` filter together cover feed, search, Shorts and player ads. YouMod also hides the following, which are not ported:
- the Premium button on page headers
- the Premium section in settings (`updateUnlimitedSectionWithEntry:`)
- the paid-promo badge on the floating miniplayer

### LiveContainer
- The "Open in YouTube" Safari extension doesn't run (LiveContainer has no app extensions).
- Don't also add these tweaks through LiveContainer's tweak folder, or they load twice.
- Cast: YTLite 5.2's notes say Cast doesn't work on newer YouTube for sideloaded builds.
- Crash logs appear as `LiveContainer-*.ips` in Settings → Privacy & Security → Analytics & Improvements → Analytics Data.

## Re-checking on the next YouTube version

```bash
python tools/dump_objc.py YouTube_x.y.z.ipa yt.txt                            # classes, methods (with types), ivars
python tools/remap.py yt.txt YTLite.x Sideloading.x YTNativeShare.x Settings.x # dead hooks + suggested replacements
python tools/crash_audit.py yt.txt .                                          # KVC / declared APIs / class lookups
```

- `remap.py` checks each hook per class, including superclasses. A hook on a missing class or method silently does nothing.
- `crash_audit.py` lists declared YouTube APIs that are gone. Calling one crashes, so filter out methods the tweak adds itself (`%new`).
- Check argument types from the dump's type encodings (for example `v24@0:8d16` means a `double`) before calling a renamed method.
- Watch for the `Foo` → `FooImpl` pattern: the old name then only survives as a protocol.
