import os
import cv2
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from stegano.lsb import hide, reveal

app = Flask(_name_)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["SECRET_KEY"] = "supersecretkey"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

def encode_video(input_video, hidden_text, output_video="output_lossless.avi"):
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        return "Error: Could not open video file."

    frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Use FFV1 (lossless codec)
    fourcc = cv2.VideoWriter_fourcc(*'F', 'F', 'V', '1')
     #  Change to XVID (More Supported) or MJPG if needed
    # fourcc = cv2.VideoWriter_fourcc(*'X', 'V', 'I', 'D')
    out = cv2.VideoWriter(output_video, fourcc, frame_rate, (frame_width, frame_height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert frame to PNG format (lossless) before encoding
        frame_path = "temp_frame.png"
        cv2.imwrite(frame_path, frame)

        # Hide the message in every frame
        stego_frame = hide(frame_path, hidden_text)
        stego_frame.save(frame_path)

        # Reload the frame with encoded data
        encoded_frame = cv2.imread(frame_path)
        out.write(encoded_frame)

    cap.release()
    out.release()

    return output_video


def decode_video(input_video):
    print(f" Opening video file: {input_video}")  # Debugging

    cap = cv2.VideoCapture(input_video)

    if not cap.isOpened():
        return "Error: Could not open video file."

    success, frame = cap.read()

    if not success:
        return "Error: No frames found in the video!"

    temp_frame_path = "temp_decode.png"
    cv2.imwrite(temp_frame_path, frame)

    try:
        extracted_text = reveal(temp_frame_path)
        if extracted_text:
            return f" Extracted hidden text: {extracted_text}"
        else:
            return "No hidden text found."
    except Exception as e:
        return f"Error: Could not reveal the hidden text! {e}"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "video" not in request.files or "message" not in request.form:
            flash("Please upload a video and enter a message.")
            return redirect(request.url)

        video = request.files["video"]
        message = request.form["message"]

        if video.filename == "":
            flash("No selected file.")
            return redirect(request.url)

        filename = secure_filename(video.filename)
        video_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        video.save(video_path)

        result = encode_video(video_path, message)
        flash(result)
        return redirect(request.url)

    return render_template("index.html")


@app.route("/decode", methods=["POST"])
def decode():
    if "video" not in request.files:
        flash("Please upload a video.")
        return redirect(url_for("index"))

    video = request.files["video"]

    if video.filename == "":
        flash("No file selected.")
        return redirect(url_for("index"))

    filename = secure_filename(video.filename)
    video_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    video.save(video_path)  # Save the uploaded video

    # Debugging: Check if file exists
    if not os.path.exists(video_path):
        flash(f" Error: Uploaded file {filename} not found on the server!")
        return redirect(url_for("index"))

    flash(f" File {filename} uploaded successfully.")
    
    # Now try to decode
    extracted_text = decode_video(video_path)

    flash(extracted_text)
    return redirect(url_for("index"))


if _name_ == "_main_":
    app.run(debug=True)
