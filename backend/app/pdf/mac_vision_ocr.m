#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <AppKit/AppKit.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "Usage: mac_vision_ocr <image_path>\n");
            return 1;
        }
        
        NSString *imagePath = [NSString stringWithUTF8String:argv[1]];
        NSURL *imageUrl = [NSURL fileURLWithPath:imagePath];
        NSImage *image = [[NSImage alloc] initWithContentsOfURL:imageUrl];
        if (!image) {
            fprintf(stderr, "Failed to load image: %s\n", argv[1]);
            return 2;
        }
        
        CGImageRef cgImage = [image CGImageForProposedRect:nil context:nil hints:nil];
        if (!cgImage) {
            fprintf(stderr, "Failed to get CGImage\n");
            return 3;
        }
        
        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.recognitionLanguages = @[@"ar", @"ar-SA", @"en-US"];
        request.usesLanguageCorrection = YES;
        
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:cgImage options:@{}];
        NSError *error = nil;
        [handler performRequests:@[request] error:&error];
        
        if (error) {
            fprintf(stderr, "Vision OCR error: %s\n", [[error localizedDescription] UTF8String]);
            return 4;
        }
        
        for (VNRecognizedTextObservation *obs in request.results) {
            NSArray<VNRecognizedText *> *candidates = [obs topCandidates:1];
            if (candidates.count > 0) {
                printf("%s\n", [candidates[0].string UTF8String]);
            }
        }
    }
    return 0;
}
