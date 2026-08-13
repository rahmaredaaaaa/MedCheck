import cv2

for index in range(5):

    print(f"\nTesting camera index: {index}")

    camera = cv2.VideoCapture(index, cv2.CAP_MSMF)

    if not camera.isOpened():
        print("Could not open")
        camera.release()
        continue

    print("Opened")

    success, frame = camera.read()

    if success and frame is not None:
        print("FRAME RECEIVED!")

        cv2.imshow(
            f"Camera {index}",
            frame
        )

        cv2.waitKey(3000)

        camera.release()
        cv2.destroyAllWindows()

        print(f"WORKING CAMERA INDEX = {index}")
        break

    else:
        print("Opened but NO FRAME")

    camera.release()

cv2.destroyAllWindows()