from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse
from src.database.db import get_db
from src.database.models import Image
from src.services.cloudinary_srv import cloudinary
import cloudinary
from cloudinary.uploader import upload
import cloudinary.api
import qrcode
from io import BytesIO
import cloudinary.utils

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.conf.config import settings
from src.conf import messages


class CloudinaryService:
    cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


cloud_router = APIRouter(prefix="/cloudinary", tags=["Cloudinary image operations"])


@cloud_router.get("/transformed_image/{image_id}")
def transform_and_update_image(
    image_id: str, angle: int = 45, db: Session = Depends(get_db)
):
    image = db.query(Image).filter(Image.id == image_id).first()
    print("1:", image)
    print("Start:", image_id)

    if image:
        url_original = image.url_original
        public_id = cloudinary.utils.cloudinary_url(url_original)[0].split("/")[-1]
        print("Start URL:", url_original)

        folder_path = "transform"
        transformation = {"angle": angle}

        public_id = f"{folder_path}/{public_id}"

        response = upload(
            url_original, transformation=transformation, public_id=public_id
        )

        transformed_image_url = response["secure_url"]

        db.query(Image).filter(Image.id == image_id).update(
            {"url_transformed": transformed_image_url}
        )
        db.commit()

        print("1:", image_id)
        print("Original Image URL:", url_original)
        print("Transformed Image URL:", transformed_image_url)

        return {
            "message": f"Image transformed and updated successfully. Rotated by {angle} degrees.",
            "transformed_image_url": transformed_image_url,
        }

    return {"error": "Image not found."}


@cloud_router.get("/qr_codes_image/{image_id}")
def qr_codes_and_update_image(image_id: str, db: Session = Depends(get_db)):
    image = db.query(Image).filter(Image.id == image_id).first()
    print("1:", image)
    print("Start:", image_id)

    if image:
        url_original = image.url_original
        public_id = cloudinary.utils.cloudinary_url(url_original)[0].split("/")[-1]
        print("Start URL:", url_original)

        folder_path = "qr_codes"

        # Create QR
        qr_original = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr_original.add_data(url_original)
        qr_original.make(fit=True)

        # Save QR
        qr_code_original_image = qr_original.make_image(
            fill_color="black", back_color="white"
        )
        qr_code_original_image_io = BytesIO()
        qr_code_original_image.save(qr_code_original_image_io, format="PNG")

        # Upload QR
        qr_code_original_response = upload(
            qr_code_original_image_io.getvalue(),
            folder=folder_path,
            public_id=f"{folder_path}/{public_id}_qr_code",
            format="png",
            overwrite=True,
        )

        qr_code_original_url = qr_code_original_response["secure_url"]

        db.query(Image).filter(Image.id == image_id).update(
            {"url_original_qr": qr_code_original_url}
        )
        db.commit()

        print("1:", image_id)
        print("Original Image URL:", url_original)
        print("QR Code URL for Original Image:", qr_code_original_url)

        return {
            "message": f"QR Code generated and updated successfully for the original image.",
            "url_original_qr": qr_code_original_url,
        }

    return {"error": "Image not found."}


@cloud_router.get("/qr_load/{image_id}")
def qr_codes_image_load(
    image_id: str,
    option: str
    | None = Query(
        title="Type of source of image to use", default="original", description="Type of source of image to use. Can be: original or transformed. By default used  original"
    ),
    db: Session = Depends(get_db),
):
    image: Image = db.query(Image).filter(Image.id == image_id).first()
    if image:
        qr_original = qrcode.QRCode( # type: ignore
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M, # type: ignore
            box_size=10,
            border=4,
        )
        url_str: str = (
            image.url_transformed if option == "transformed" else image.url_original
        ) # type: ignore
        if url_str:
            qr_original.add_data(url_str)
            qr_original.make(fit=True)

            # Save QR
            qr_code_original_image = qr_original.make_image(
                fill_color="black", back_color="white"
            )
            qr_code_original_image_io = BytesIO()
            qr_code_original_image.save(qr_code_original_image_io, format="PNG")
            qr_code_original_image_io.seek(0)  # Return cursor to starting point
            return StreamingResponse(qr_code_original_image_io, media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=messages.IMG_NOT_FOUND
    )
