from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import decimal
import hashlib
from tg_bot import successful_payment

app = FastAPI()

# Константы
MERCHANT_PASSWORD_2 = "T6XAvZ94G8drrHOCeMx1"  # Замени на свой пароль #2

def calculate_signature(*args) -> str:
    """Создаёт MD5 подпись для запроса."""
    signature = hashlib.md5(':'.join(str(arg) for arg in args).encode()).hexdigest()
    return signature


def check_signature_result(
    order_number: int,  # Номер счета (InvId)
    received_sum: decimal.Decimal,  # Сумма из запроса (OutSum)
    received_signature: str,  # Подпись (SignatureValue)
    password: str,  # Пароль #2
    additional_params: dict  # Дополнительные параметры для расчета подписи
) -> bool:
    """Проверка подписи на соответствие."""

    signature_data = [str(received_sum), str(order_number), password]

    if additional_params:
        for key, value in additional_params.items():
            signature_data.append(f"{key}={value}")

    signature = calculate_signature(*signature_data)
    return signature.lower() == received_signature.lower()


def parse_response(request_str: str) -> dict:
    """Парсит строку запроса и возвращает словарь параметров."""
    params = {}
    for item in request_str.split('&'):
        key, value = item.split('=')
        params[key] = value
    return params

@app.post("/result/")
async def result(request: Request):
    """Обработка вебхука от Robokassa и проверка подписи."""

    try:
        # Получаем строку запроса
        request_data = await request.body()
        request_str = request_data.decode("utf-8")  # Декодируем запрос

        # Парсим запрос
        param_request = parse_response(request_str)

        # Проверка, что параметры есть в запросе
        if param_request:
            # Извлекаем нужные параметры
            cost = decimal.Decimal(param_request.get('OutSum', '0'))  # Сумма платежа
            number = int(param_request.get('InvId', '0'))  # Номер заказа
            signature = param_request.get('SignatureValue', '')  # Подпись от Робокассы

            # Ваши пользовательские параметры (например, Shp_user_id)
            additional_params = {
                'Shp_user_id': param_request.get('Shp_user_id', '')  # Пользовательский параметр
            }

            # Проверка подписи
            if check_signature_result(number, cost, signature, MERCHANT_PASSWORD_2, additional_params):
                # Если подпись верна, выполняем успешную оплату
                await successful_payment(number, int(additional_params.get('Shp_user_id', 0)))
                return JSONResponse(content={"status": "success", "message": f"OK{param_request.get('InvId')}"})
            else:
                # Если подпись неверна
                return JSONResponse(content={"status": "error", "message": "Bad signature"}, status_code=400)

        else:
            # Если параметры не найдены в запросе
            return JSONResponse(content={"status": "error", "message": "Missing parameters in the request"}, status_code=400)

    except Exception as e:
        # Логируем ошибку
        return JSONResponse(content={"status": "error", "message": f"Error processing request: {str(e)}"}, status_code=400)


    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return JSONResponse(content={"status": "error", "message": f"Error: {str(e)}"}, status_code=400)


# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
