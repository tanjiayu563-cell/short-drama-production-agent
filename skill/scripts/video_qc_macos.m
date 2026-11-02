#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreMedia/CoreMedia.h>
#import <ImageIO/ImageIO.h>
#import <CoreGraphics/CoreGraphics.h>

static void fail(NSString *message) {
    fprintf(stderr, "error: %s\n", message.UTF8String);
    exit(2);
}

static NSInteger parseInteger(NSString *value, NSInteger fallback) {
    NSScanner *scanner = [NSScanner scannerWithString:value];
    NSInteger result = 0;
    return [scanner scanInteger:&result] ? result : fallback;
}

static BOOL writeJPEG(CGImageRef image, NSURL *url, CGFloat quality, NSError **error) {
    CGImageDestinationRef destination = CGImageDestinationCreateWithURL(
        (__bridge CFURLRef)url, CFSTR("public.jpeg"), 1, NULL
    );
    if (!destination) {
        if (error) *error = [NSError errorWithDomain:@"video_qc" code:10 userInfo:@{NSLocalizedDescriptionKey: @"Could not create JPEG destination"}];
        return NO;
    }
    NSDictionary *properties = @{(__bridge NSString *)kCGImageDestinationLossyCompressionQuality: @(quality)};
    CGImageDestinationAddImage(destination, image, (__bridge CFDictionaryRef)properties);
    BOOL ok = CGImageDestinationFinalize(destination);
    CFRelease(destination);
    if (!ok && error) {
        *error = [NSError errorWithDomain:@"video_qc" code:11 userInfo:@{NSLocalizedDescriptionKey: @"Could not write JPEG"}];
    }
    return ok;
}

static BOOL makeContactSheet(NSArray<id> *images, NSURL *url, NSError **error) {
    const size_t tileWidth = 320;
    const size_t tileHeight = 568;
    const size_t columns = 4;
    const size_t rows = 6;
    const size_t margin = 8;
    const size_t padding = 8;
    const size_t width = margin * 2 + columns * tileWidth + (columns - 1) * padding;
    const size_t height = margin * 2 + rows * tileHeight + (rows - 1) * padding;
    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
    CGContextRef context = CGBitmapContextCreate(
        NULL, width, height, 8, 0, colorSpace,
        kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big
    );
    CGColorSpaceRelease(colorSpace);
    if (!context) {
        if (error) *error = [NSError errorWithDomain:@"video_qc" code:20 userInfo:@{NSLocalizedDescriptionKey: @"Could not create contact sheet context"}];
        return NO;
    }
    CGContextSetRGBFillColor(context, 0.06, 0.06, 0.06, 1.0);
    CGContextFillRect(context, CGRectMake(0, 0, width, height));
    CGContextSetInterpolationQuality(context, kCGInterpolationHigh);
    NSUInteger count = MIN(images.count, columns * rows);
    for (NSUInteger index = 0; index < count; index++) {
        CGImageRef image = (__bridge CGImageRef)images[index];
        size_t row = index / columns;
        size_t column = index % columns;
        CGFloat x = margin + column * (tileWidth + padding);
        CGFloat y = height - margin - (row + 1) * tileHeight - row * padding;
        CGRect target = CGRectMake(x, y, tileWidth, tileHeight);
        CGContextSetRGBFillColor(context, 0.12, 0.12, 0.12, 1.0);
        CGContextFillRect(context, target);
        CGFloat imageWidth = (CGFloat)CGImageGetWidth(image);
        CGFloat imageHeight = (CGFloat)CGImageGetHeight(image);
        CGFloat scale = MIN(tileWidth / imageWidth, tileHeight / imageHeight);
        CGFloat drawWidth = imageWidth * scale;
        CGFloat drawHeight = imageHeight * scale;
        CGRect drawRect = CGRectMake(
            x + (tileWidth - drawWidth) / 2.0,
            y + (tileHeight - drawHeight) / 2.0,
            drawWidth,
            drawHeight
        );
        CGContextDrawImage(context, drawRect, image);
    }
    CGImageRef sheet = CGBitmapContextCreateImage(context);
    CGContextRelease(context);
    if (!sheet) {
        if (error) *error = [NSError errorWithDomain:@"video_qc" code:21 userInfo:@{NSLocalizedDescriptionKey: @"Could not render contact sheet"}];
        return NO;
    }
    BOOL ok = writeJPEG(sheet, url, 0.85, error);
    CGImageRelease(sheet);
    return ok;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSString *input = nil;
        NSString *output = nil;
        NSInteger maxFrames = 24;
        NSNumber *intervalValue = nil;
        for (int i = 1; i < argc; i++) {
            NSString *arg = [NSString stringWithUTF8String:argv[i]];
            if ([arg isEqualToString:@"--input"] && i + 1 < argc) {
                input = [NSString stringWithUTF8String:argv[++i]];
            } else if ([arg isEqualToString:@"--output-dir"] && i + 1 < argc) {
                output = [NSString stringWithUTF8String:argv[++i]];
            } else if ([arg isEqualToString:@"--max-frames"] && i + 1 < argc) {
                maxFrames = parseInteger([NSString stringWithUTF8String:argv[++i]], 24);
            } else if ([arg isEqualToString:@"--interval"] && i + 1 < argc) {
                intervalValue = @([[NSString stringWithUTF8String:argv[++i]] doubleValue]);
            } else {
                fail([NSString stringWithFormat:@"unknown argument: %@", arg]);
            }
        }
        if (!input || !output) {
            fail(@"usage: video_qc_macos --input VIDEO --output-dir DIR [--max-frames 24] [--interval SECONDS]");
        }
        if (maxFrames < 1 || maxFrames > 100) fail(@"--max-frames must be between 1 and 100");
        if (intervalValue && intervalValue.doubleValue <= 0) fail(@"--interval must be positive");

        NSFileManager *fm = NSFileManager.defaultManager;
        if (![fm fileExistsAtPath:input]) fail([NSString stringWithFormat:@"video not found: %@", input]);
        NSError *dirError = nil;
        NSString *framesPath = [output stringByAppendingPathComponent:@"frames"];
        [fm createDirectoryAtPath:framesPath withIntermediateDirectories:YES attributes:nil error:&dirError];
        if (dirError) fail([NSString stringWithFormat:@"could not create output directory: %@", dirError.localizedDescription]);

        AVURLAsset *asset = [AVURLAsset URLAssetWithURL:[NSURL fileURLWithPath:input] options:nil];
        double duration = CMTimeGetSeconds(asset.duration);
        if (!isfinite(duration) || duration <= 0) fail(@"could not read a positive video duration");
        NSArray<AVAssetTrack *> *videoTracks = [asset tracksWithMediaType:AVMediaTypeVideo];
        AVAssetTrack *track = videoTracks.firstObject;
        if (!track) fail(@"no video track found");
        CGRect transformed = CGRectApplyAffineTransform(
            CGRectMake(0, 0, track.naturalSize.width, track.naturalSize.height),
            track.preferredTransform
        );
        NSInteger width = (NSInteger)llround(fabs(transformed.size.width));
        NSInteger height = (NSInteger)llround(fabs(transformed.size.height));
        double fps = track.nominalFrameRate;
        NSInteger audioCount = (NSInteger)[asset tracksWithMediaType:AVMediaTypeAudio].count;

        double interval = intervalValue ? intervalValue.doubleValue : MAX(0.1, duration / (double)maxFrames);
        NSMutableArray<NSNumber *> *timestamps = [NSMutableArray array];
        for (double t = 0.0; t < duration && (NSInteger)timestamps.count < maxFrames; t += interval) {
            [timestamps addObject:@(t)];
        }
        if (timestamps.count == 0) [timestamps addObject:@(0.0)];

        AVAssetImageGenerator *generator = [[AVAssetImageGenerator alloc] initWithAsset:asset];
        generator.appliesPreferredTrackTransform = YES;
        generator.requestedTimeToleranceBefore = kCMTimeZero;
        generator.requestedTimeToleranceAfter = kCMTimeZero;

        NSMutableArray<NSDictionary *> *frameEntries = [NSMutableArray array];
        NSMutableArray<id> *contactFrames = [NSMutableArray array];
        for (NSUInteger index = 0; index < timestamps.count; index++) {
            double seconds = MIN(timestamps[index].doubleValue, MAX(0.0, duration - 0.001));
            CMTime time = CMTimeMakeWithSeconds(seconds, 600);
            NSError *imageError = nil;
            CGImageRef image = [generator copyCGImageAtTime:time actualTime:NULL error:&imageError];
            if (!image) {
                fprintf(stderr, "warning: frame at %.3fs failed: %s\n", seconds, imageError.localizedDescription.UTF8String);
                continue;
            }
            NSString *filename = [NSString stringWithFormat:@"frame_%03lu.jpg", (unsigned long)index + 1];
            NSURL *frameURL = [NSURL fileURLWithPath:[framesPath stringByAppendingPathComponent:filename]];
            NSError *writeError = nil;
            if (!writeJPEG(image, frameURL, 0.88, &writeError)) {
                fprintf(stderr, "warning: could not write frame %.3fs: %s\n", seconds, writeError.localizedDescription.UTF8String);
                CGImageRelease(image);
                continue;
            }
            [frameEntries addObject:@{
                @"index": @(index + 1),
                @"timestamp": @(round(seconds * 1000.0) / 1000.0),
                @"path": frameURL.path
            }];
            [contactFrames addObject:(__bridge id)image];
            CGImageRelease(image);
        }

        NSString *contactPath = [output stringByAppendingPathComponent:@"contact-sheet.jpg"];
        NSError *contactError = nil;
        BOOL contactOK = contactFrames.count > 0 && makeContactSheet(contactFrames, [NSURL fileURLWithPath:contactPath], &contactError);
        if (!contactOK && contactError) {
            fprintf(stderr, "warning: contact sheet failed: %s\n", contactError.localizedDescription.UTF8String);
        }

        NSDictionary *attributes = [fm attributesOfItemAtPath:input error:nil];
        NSNumber *fileSize = attributes[NSFileSize] ?: @0;
        NSDictionary *meta = @{
            @"backend": @"macos-avfoundation",
            @"duration_seconds": @(duration),
            @"width": @(width),
            @"height": @(height),
            @"aspect_ratio": height > 0 ? @((double)width / (double)height) : NSNull.null,
            @"fps": @(fps),
            @"has_audio": audioCount > 0 ? @YES : @NO,
            @"audio_streams": @(audioCount),
            @"format_name": input.pathExtension.lowercaseString ?: @"",
            @"size_bytes": fileSize,
            @"bit_rate": NSNull.null,
            @"interval_seconds": @(interval),
            @"frame_count": @(frameEntries.count),
            @"frames": frameEntries,
            @"contact_sheet": contactOK ? contactPath : NSNull.null,
            @"technical_scan_available": @NO
        };
        NSError *jsonError = nil;
        NSData *data = [NSJSONSerialization dataWithJSONObject:meta options:NSJSONWritingPrettyPrinted | NSJSONWritingSortedKeys error:&jsonError];
        if (!data) fail([NSString stringWithFormat:@"could not encode metadata: %@", jsonError.localizedDescription]);
        NSString *metaPath = [output stringByAppendingPathComponent:@"macos-meta.json"];
        if (![data writeToFile:metaPath options:NSDataWritingAtomic error:&jsonError]) {
            fail([NSString stringWithFormat:@"could not write metadata: %@", jsonError.localizedDescription]);
        }
        printf("%s\n", metaPath.UTF8String);
    }
    return 0;
}
