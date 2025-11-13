"""
Microphone permission helper for macOS using AVFoundation (PyObjC)
Forces a permission prompt on first launch and returns True if authorized.
"""

import sys

def ensure_mic_permission(timeout_seconds: float = 10.0) -> bool:
    try:
        import AVFoundation
        from Foundation import NSRunLoop, NSDate

        status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
            AVFoundation.AVMediaTypeAudio
        )
        if status == AVFoundation.AVAuthorizationStatusAuthorized:
            return True
        if status == AVFoundation.AVAuthorizationStatusDenied:
            return False
        if status == AVFoundation.AVAuthorizationStatusRestricted:
            return False

        # Not determined: request access and spin the run loop until user responds
        granted_box = {"granted": None}

        def handler(granted: bool):
            granted_box["granted"] = bool(granted)

        AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVFoundation.AVMediaTypeAudio, handler
        )

        # Wait up to timeout_seconds for user response
        steps = int(timeout_seconds * 10)
        for _ in range(steps):
            NSRunLoop.currentRunLoop().runUntilDate_(
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
            if granted_box["granted"] is not None:
                return granted_box["granted"]

        # Timed out (user didn't respond yet)
        return False

    except Exception as e:
        # If PyObjC/AVFoundation is unavailable, fall back to best-effort
        # The system should still prompt when opening the audio stream.
        sys.stderr.write(f"[MIC] Permission helper unavailable: {e}\n")
        return False

